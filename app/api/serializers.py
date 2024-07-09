from core.serializers import (
    Email2FASerializer,
    SMS2FASerializer,
    TOTPSerializer,
)
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

User = get_user_model()


class MFAListSerializer(serializers.Serializer):
    totps = TOTPSerializer(many=True)
    sms = SMS2FASerializer(many=True)
    email = Email2FASerializer(many=True)


class EmailPasswordSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()
    remember = serializers.BooleanField(required=False)
    bypass_token = serializers.CharField(required=False)

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        email = validated_data["email"]
        password = validated_data["password"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid email address.")
        password_valid = user.check_password(password)
        if not password_valid:
            raise ValidationError("Invalid password.")

        bypass_token = validated_data.get("bypass_token")

        if bypass_token:
            if bypass_token != settings.COOKIE_BYPASS_TOKEN:
                raise ValidationError("Invalid bypass token.")

        return {
            "tokens": user.get_auth_tokens(),
            "remember": validated_data.get("remember", False),
            "bypass_token": validated_data.get("bypass_token"),
        }
