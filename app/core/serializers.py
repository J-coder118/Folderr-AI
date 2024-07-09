import logging
from datetime import datetime

import pyotp
from backend.aws_setup import download
from core.models import (
    SMS2FA,
    TOTP,
    Email2FA,
    FolderrEmail,
    FolderrEmailAttachment,
    User,
)
from core.tasks import send_email
from core.utils import recaptcha_valid
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

log = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["avatar"] = download(instance.avatar.name, allow_download=True)
        rep["is_plus"] = instance.is_plus
        rep["can_scan_receipt"] = instance.can_scan_receipt
        rep["can_create_asset"] = instance.can_create_asset
        rep["can_receive_email"] = instance.can_receive_email
        rep["storage_used"] = instance.storage_bytes_used
        rep["max_storage"] = instance.max_storage
        rep["requires_mfa"] = instance.requires_2fa
        return rep

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "avatar",
            "membership",
            "first_name",
            "last_name",
            "profile_complete",
            "random_email",
            "revenue_cat_app_user_id",
            "user_type",
        ]


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        max_length=128, style={"input_type": "password"}, write_only=True
    )
    recaptcha_response = serializers.CharField(write_only=True)
    organization_pin = serializers.CharField(write_only=True, required=False)

    def validate_recaptcha_response(self, value):
        is_valid = recaptcha_valid(value)
        if is_valid is False:
            raise ValidationError(
                "You're a spammer or did something too quickly. Please try again."
            )
        return value

    def validate_organization_pin(self, value):
        if value is not None:
            if value != settings.SUNRUN_ORGANIZATION_PIN:
                raise ValidationError("Invalid PIN.")
        return value

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "phone_number",
            "terms_agreed",
            "recaptcha_response",
            "organization_pin",
        ]

    def create(self, validated_data):
        validated_data.pop("recaptcha_response")
        organization_pin = validated_data.pop("organization_pin", None)
        user_type = User.NORMAL_USER_TYPE
        if organization_pin is not None:
            if organization_pin == settings.SUNRUN_ORGANIZATION_PIN:
                user_type = User.SUNRUN_EMPLOYEE_USER_TYPE
        return User.objects.create_user(**validated_data, user_type=user_type)


class UserObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        user_serializer = UserSerializer(user)
        token["user"] = user_serializer.data
        user.last_login = timezone.now()
        user.save()
        return token


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super(CustomTokenRefreshSerializer, self).validate(attrs)
        return data


class PasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)

    class Meta:
        fields = ["email"]

    def validate(self, attrs):
        email = attrs.get("email", "")
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            uidb64 = urlsafe_base64_encode(str(user.id).encode())
            token = PasswordResetTokenGenerator().make_token(user)
            # request = self.context.get('request')
            # current_site = request.build_absolute_uri('/')[:-1].strip("/")
            abs_url = f"https://folderr.com/resetpassword/{uidb64}/{token}"
            email_body = f"Hi {user.first_name} {user.last_name},\nPlease use the link below to verify your email.\n{abs_url}"

            print(f"CLICK TO RESET PASSWORD: {abs_url}")

            # TODO Send Mail. Find a replacement for Google's SMTP.

            send_email.delay(
                subject="Password Reset",
                body=email_body,
                sender=settings.DEFAULT_FROM_EMAIL,
                recipients=[email],
                fail_silently=False,
            )

            return super().validate(attrs)
        raise serializers.ValidationError(
            "Entered email address is wrong, Try Again !"
        )


class PasswordResetOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    class Meta:
        fields = ["phone_number"]


class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    confirm_password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )

    class Meta:
        fields = ["password", "confirm_password"]

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")
        uidb64 = self.context.get("uidb64")
        token = self.context.get("token")

        if password != confirm_password:
            raise serializers.ValidationError(
                "Password and Confirm Password do not match."
            )
        id = smart_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=id)
        if not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError(
                "Token is either invalid or expired."
            )
        user.set_password(password)
        user.save()
        return attrs


class OTPValidateSerializer(serializers.Serializer):
    otp = serializers.CharField()
    phone_number = serializers.CharField()

    class Meta:
        fields = ["phone_number", "otp"]

    def validate(self, attrs):
        otp = attrs.get("otp")
        phone_number = attrs.get("phone_number")
        try:
            user = User.objects.get(otp=otp, phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP.")

        datetime_diff = (
            int(datetime.utcnow().strftime("%s"))
            - int(user.otp_expires.strftime("%s"))
        ) / 60
        if datetime_diff > 15:
            raise serializers.ValidationError("OTP expired.")
        return attrs


class PasswordResetConfirmOTPSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    confirm_password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    otp = serializers.CharField()
    phone_number = serializers.CharField()

    class Meta:
        fields = ["password", "confirm_password", "otp", "phone_number"]

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")
        otp = attrs.get("otp")
        phone_number = attrs.get("phone_number")
        try:
            user = User.objects.get(otp=otp, phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"phone number": "Record not found!."}
            )
        if password != confirm_password:
            raise serializers.ValidationError(
                {
                    "confirm_password": "Password and Confirm Password do not match."
                }
            )
        user.otp = None
        user.otp_expires = None
        user.set_password(password)
        user.save()
        return attrs


class UpdateProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["is_plus"] = instance.is_plus
        rep["avatar"] = download(instance.avatar.name)
        return rep

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "avatar",
            "is_verified",
            "phone_number",
            "membership",
            "profile_complete",
            "random_email",
            "revenue_cat_app_user_id",
        ]


class UpdateProfileAvatar(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "avatar"]

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res["avatar"] = download(instance.avatar.name)

        return res


class ChangePasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    new_password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    confirm_password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )

    class Meta:
        model = User
        fields = ["old_password", "new_password", "confirm_password"]

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs.get("old_password")):
            raise serializers.ValidationError(
                "Your current password is incorrect."
            )
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")
        if new_password != confirm_password:
            raise serializers.ValidationError(
                "Password and Confirm Password do not match."
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.get("new_password")
        user = self.context["request"].user
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "password",
            "phone_number",
            "terms_agreed",
        ]


class ContactUsSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    email = serializers.EmailField(max_length=256)
    msg = serializers.CharField()


class UserSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "avatar", "first_name", "last_name"]


class FolderrEmailAttachmentSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = download(instance.file.name, allow_download=True)
        rep["thumbnail"] = download(
            instance.thumbnail.name, allow_download=True
        )
        return rep

    class Meta:
        model = FolderrEmailAttachment
        exclude = ["email"]


class FolderrEmailSerializer(serializers.ModelSerializer):
    attachments = FolderrEmailAttachmentSerializer(many=True)

    def validate(self, attrs):
        asset = attrs.get("asset")
        if asset:
            user = self.context["request"].user
            if asset.created_by != user:
                log.info(
                    "User %d is trying to set FolderrEmail asset to %d which he doesn't own.",
                    user.pk,
                    asset.pk,
                )
                raise ValidationError("You don't own this folder.")
        return attrs

    class Meta:
        model = FolderrEmail
        exclude = ["s3_object_key", "user"]


class TOTPSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        totp = TOTP(**validated_data)
        totp.user = self.context["request"].user
        secret = pyotp.random_base32()
        totp.secret = secret
        hotp = pyotp.HOTP(secret)
        backup_codes = []
        for i in range(10):
            backup_codes.append(hotp.at(i))
        totp.backup_codes = backup_codes
        totp.save()
        return totp

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.requested is False:
            rep["backup_codes"] = instance.backup_codes
            rep["secret"] = instance.secret
            rep["provisioning_uri"] = instance.provisioning_uri
            instance.requested = True
            instance.save()
        return rep

    class Meta:
        model = TOTP
        fields = ["id", "name", "active"]
        read_only_fields = ["id"]


class SMS2FASerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        sms_2fa = SMS2FA(**validated_data)
        sms_2fa.user = self.context["request"].user
        sms_2fa.secret = pyotp.random_base32()
        sms_2fa.save()
        return sms_2fa

    class Meta:
        model = SMS2FA
        fields = ["id", "phone_number", "active"]
        read_only_fields = ["id"]


class Email2FASerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        email_2fa = Email2FA(**validated_data)
        email_2fa.user = self.context["request"].user
        email_2fa.secret = pyotp.random_base32()
        email_2fa.save()
        return email_2fa

    class Meta:
        model = Email2FA
        fields = ["id", "active"]
        read_only_fields = ["id"]
