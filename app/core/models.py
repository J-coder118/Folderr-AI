from __future__ import unicode_literals

import logging
import mimetypes
import secrets
import string
import uuid
from io import BytesIO

import boto3
import pyotp
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.files.images import ImageFile
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from djstripe.models import Customer
from pdf2image import pdf2image
from phonenumber_field.modelfields import PhoneNumberField
from PIL import Image, ImageOps
from rest_framework_simplejwt.tokens import RefreshToken

from .managers import UserManager
from .revenue_cat import RevenueCat

AUTH_PROVIDERS = {
    "facebook": "facebook",
    "google": "google",
    "email": "email",
    "apple": "apple",
}

log = logging.getLogger(__name__)


def upload_avatar_to(instance, filename):
    return f"avatars/{instance.id}/{filename}"


class User(AbstractBaseUser, PermissionsMixin):
    FREE_MEMBERSHIP = 0
    PLUS_MEMBERSHIP = 1
    MEMBERSHIP_CHOICES = (
        (FREE_MEMBERSHIP, "Folderr Free"),
        (PLUS_MEMBERSHIP, "Folderr Plus"),
    )
    NORMAL_USER_TYPE = 0
    SUNRUN_ADMIN_USER_TYPE = 1
    SUNRUN_EMPLOYEE_USER_TYPE = 2
    USER_TYPE_CHOICES = (
        (NORMAL_USER_TYPE, "Normal"),
        (SUNRUN_ADMIN_USER_TYPE, "Sunrun Admin"),
        (SUNRUN_EMPLOYEE_USER_TYPE, "Sunrun Employee"),
    )

    email = models.EmailField(
        _("email address"), unique=True, blank=False, null=False
    )
    first_name = models.CharField(
        max_length=100, blank=False, null=False, default="Fname"
    )
    last_name = models.CharField(
        max_length=100, blank=False, null=False, default="Lname"
    )
    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)
    avatar = models.ImageField(
        upload_to=upload_avatar_to, null=True, blank=True
    )
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    terms_agreed = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_expires = models.DateTimeField(auto_now_add=True, null=True)
    is_verified = models.BooleanField(default=False)
    auth_provider = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default=AUTH_PROVIDERS.get("email"),
    )
    profile_complete = models.BooleanField(default=True)
    random_email = models.BooleanField(default=False)

    apple_subject = models.CharField(
        max_length=64,
        editable=False,
        null=False,
        blank=True,
        help_text="Apple subject registered claim.",
    )
    membership = models.PositiveSmallIntegerField(
        choices=MEMBERSHIP_CHOICES, default=FREE_MEMBERSHIP
    )

    receipt_scans = models.PositiveSmallIntegerField(default=0)

    emails_received = models.PositiveSmallIntegerField(default=0)

    storage_bytes_used = models.PositiveBigIntegerField(default=0)

    revenue_cat_app_user_id = models.UUIDField(default=uuid.uuid4)

    user_type = models.PositiveSmallIntegerField(
        choices=USER_TYPE_CHOICES, default=NORMAL_USER_TYPE
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return f"{self.email} ({self.get_membership_display()})"

    @property
    def requires_2fa(self):
        return (
            self.totps.filter(active=True).count() > 0
            or self.sms_2fas.filter(active=True).count() > 0
            or self.email_2fas.filter(active=True).count() > 0
        )

    @property
    def is_plus(self):
        return self.membership == self.PLUS_MEMBERSHIP

    @property
    def max_assets(self):
        if self.is_plus:
            return 20
        return 3

    @property
    def max_storage(self):
        if self.is_plus:
            return 100 * 1073741824
        return 5 * 1073741824

    @property
    def max_emails(self):
        if self.is_plus:
            return None
        return 100

    @property
    def can_receive_email(self):
        if self.is_plus:
            return True
        if self.max_emails < self.emails_received:
            return True
        return False

    @property
    def asset_count(self):
        return self.folder_set.filter(is_root=True).count()

    @property
    def can_create_asset(self):
        return self.asset_count < self.max_assets

    @property
    def max_receipt_scans(self):
        if self.is_plus:
            return 100
        return 10

    @property
    def can_scan_receipt(self):
        if self.receipt_scans < self.max_receipt_scans:
            return True
        return False

    def can_upload(self, file_size: int | None = None):
        if file_size:
            next_storage = self.storage_bytes_used + file_size
            if next_storage < self.max_storage:
                return True
            else:
                return False
        if self.storage_bytes_used < self.max_storage:
            return True

        return False

    def record_receipt_scan(self):
        log.info("Recording receipt scan for user %d", self.pk)
        self.receipt_scans += 1
        self.save()

    def record_disk_usage(self, file_size: int):
        self.storage_bytes_used += file_size
        self.save()

    def reduce_disk_usage(self, file_size: int):
        self.storage_bytes_used -= file_size
        if self.storage_bytes_used < 0:
            self.storage_bytes_used = 0
        self.save()

    def record_email_receipt(self):
        log.info("Recording email receipt for user %d", self.pk)
        self.emails_received += 1
        self.save()

    def upgrade_to_plus(self):
        self.membership = self.PLUS_MEMBERSHIP
        self.save()

    def downgrade_to_free(self):
        self.membership = self.FREE_MEMBERSHIP
        self.save()

    def check_stripe_customer(self):
        try:
            customer = Customer.objects.get(email=self.email)
        except Customer.DoesNotExist:
            log.info("User %d isn't registered as a Stripe customer.", self.pk)
            return False
        subscription = getattr(customer, "subscription")
        if subscription is None:
            log.info("User %d's Stripe subscription expired.", self.pk)
            return False
        plan = getattr(subscription, "plan")
        product = plan.product
        if product.id == settings.FOLDERR_PLUS_SUBSCRIPTION_PRODUCT_ID:
            return True
        else:
            log.info(
                "User %d is subscribed to product %d which isn't Plus.",
                self.pk,
                product.pk,
            )
        return False

    def check_revenue_cat_customer(self):
        rc = RevenueCat()
        return rc.is_subscribed(self.revenue_cat_app_user_id)

    def sync_membership(self):
        is_active_on_stripe = self.check_stripe_customer()
        upgrade_to_plus = False
        downgrade_to_free = False
        if is_active_on_stripe:
            if not self.is_plus:
                log.info(
                    "User %d paid on Stripe, upgrading to Plus now.", self.pk
                )
                upgrade_to_plus = True
        else:
            if self.is_plus:
                log.info(
                    "User's Stripe subscription is inactive. Downgrading now.",
                    self.pk,
                )
                downgrade_to_free = True

        if is_active_on_stripe is False:
            is_active_on_revenue_cat = self.check_revenue_cat_customer()
            if is_active_on_revenue_cat:
                if not self.is_plus:
                    log.info(
                        "User %d paid on RevenueCat, will upgrade to Plus.",
                        self.pk,
                    )
                    upgrade_to_plus = True
            else:
                if self.is_plus:
                    log.info(
                        "User isn't subscribed on RevenueCat. Will downgrade.",
                        self.pk,
                    )
                    downgrade_to_free = True
        if upgrade_to_plus:
            self.upgrade_to_plus()
        elif downgrade_to_free:
            self.downgrade_to_free()

    def set_folderr_email_address(self):
        sequence = "".join(secrets.choice(string.digits) for _ in range(6))
        email = f"{sequence}@{settings.FOLDER_EMAIL_DOMAIN}"
        try:
            User.objects.get(folderr_email_address=email)
            return self.set_folderr_email_address()
        except User.DoesNotExist:
            log.debug("Folderr email set to %s for user %d", email, self.pk)
            self.folderr_email_address = email

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def update_login_timestamp(self):
        self.last_login = timezone.now()
        self.save()

    def get_auth_tokens(self, as_dict=True) -> dict | RefreshToken:
        refresh = RefreshToken.for_user(self)
        self.update_login_timestamp()
        if as_dict:
            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        return refresh


class FolderrEmail(models.Model):
    PROCESSING = 0
    PROCESSED = 1
    STATUS_CHOICES = ((PROCESSING, "Processing"), (PROCESSED, "Processed"))
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="folderr_emails"
    )
    asset = models.ForeignKey(
        "filemanager.Folder",
        on_delete=models.SET_NULL,
        related_name="folderr_emails",
        null=True,
        blank=True,
    )
    s3_object_key = models.CharField(max_length=255)
    email_from = models.EmailField()
    email_subject = models.CharField(
        max_length=255,
        blank=True,
    )
    email_message = models.TextField(blank=True)
    email_message_html = models.TextField(blank=True)
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PROCESSING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.s3_object_key


class FolderrEmailAttachment(models.Model):
    email = models.ForeignKey(
        FolderrEmail, on_delete=models.CASCADE, related_name="attachments"
    )
    title = models.CharField(max_length=255)
    file = models.FileField()
    is_image = models.BooleanField(default=True)
    thumbnail = models.ImageField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def set_thumbnail(self):
        mime_type = mimetypes.guess_type(self.file.name)[0]
        image = None
        # For file type image
        if "image" in mime_type:
            image = Image.open(self.file)

        # For file type pdf
        if "pdf" in mime_type:
            images = pdf2image.convert_from_bytes(
                self.file.read(), use_pdftocairo=True
            )
            image = images[0]
        if image:
            image = ImageOps.exif_transpose(image)

            # Thumbnail rotation
            if image.width > image.height:
                image.thumbnail((266, 145))
            else:
                image.thumbnail((145, 266))

            # if mode is not RGB then set mode to RGB for save thumbnail in JPEG
            if image.mode != "RGB":
                image = image.convert("RGB")
            # Save thumbnail to in-memory file as StringIO
            temp_thumb = BytesIO()
            image.save(temp_thumb, format="JPEG")
            temp_thumb.seek(0)

            # set save=False, otherwise it will run in an infinite loop
            django_image_file = ImageFile(
                file=temp_thumb, name=f"{str(uuid.uuid4())}.jpeg"
            )
            self.thumbnail = django_image_file


class FolderBaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class FileBaseModal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class TOTP(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="totps"
    )
    name = models.CharField(max_length=100)
    secret = models.CharField(max_length=255)
    backup_codes = models.JSONField()
    requested = models.BooleanField(default=False, editable=False)
    active = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def provisioning_uri(self):
        return pyotp.totp.TOTP(self.secret).provisioning_uri(
            name=self.user.email, issuer_name="Folderr"
        )

    def verify_totp(self, code: str):
        totp = pyotp.totp.TOTP(self.secret)
        return totp.verify(code)

    def __str__(self):
        return self.name


class Base2FA(models.Model):
    secret = models.CharField(max_length=255)
    active = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def generate_code(self):
        totp = pyotp.totp.TOTP(self.secret, interval=600)
        return totp.now()

    def check_code(self, code: str):
        totp = pyotp.totp.TOTP(self.secret, interval=600)
        return totp.verify(code)

    class Meta:
        abstract = True


class SMS2FA(Base2FA):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sms_2fas"
    )
    phone_number = PhoneNumberField()

    updated_at = models.DateTimeField(auto_now=True)

    def send_sms(self):
        message = render_to_string(
            template_name="core/otp-sms.txt",
            context={"code": self.generate_code()},
        )
        client = boto3.client(
            "sns",
            aws_access_key_id=settings.AWS_SNS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SNS_SECRET_ACCESS_KEY,
            region_name="us-east-1",
        )
        response = client.publish(
            PhoneNumber=self.phone_number.as_e164, Message=message
        )
        log.info(
            "SMS OTP sent to %s. Message id: %s", self, response["MessageId"]
        )

    def __str__(self):
        return self.phone_number.as_e164


class Email2FA(Base2FA):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_2fas"
    )

    def send_email(self):
        message = render_to_string(
            template_name="core/otp-email.txt",
            context={
                "first_name": self.user.first_name,
                "code": self.generate_code(),
            },
        )
        send_mail(
            "Your Folderr OTP Code",
            message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
        )

    def __str__(self):
        return self.user.email
