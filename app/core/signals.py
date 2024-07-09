from django.conf import settings
from django.core.files.images import ImageFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from filemanager.models import Share

from .models import SMS2FA, Email2FA, FolderrEmailAttachment, User
from .tasks import send_email_otp, send_sms_otp


@receiver(post_save, sender=User)
def update_share(sender, instance, created, **kwargs):
    if created:
        email = instance
        try:
            Share.objects.filter(receiver_email=email).update(
                receiver=instance
            )
        except Exception as e:
            print(f"Exception==>{str(e)}")


@receiver(post_save, sender=FolderrEmailAttachment)
def set_attachment_thumbnail(sender, instance, created, **kwargs):
    if created:
        instance.set_thumbnail()
        instance.save()


@receiver(post_save, sender=User)
def check_complete_profile(sender, instance, created, **kwargs):
    invalid_first_names = ["Fname", "NoFirstName", ""]
    invalid_last_names = ["Lname", "NoLastName", ""]
    save = False
    if instance.first_name in invalid_first_names:
        if instance.profile_complete:
            instance.profile_complete = False
            save = True
    else:
        if instance.profile_complete is False:
            instance.profile_complete = True
            save = True

    if instance.last_name in invalid_last_names:
        if instance.profile_complete:
            instance.profile_complete = False
            save = True
    else:
        if instance.profile_complete is False:
            instance.profile_complete = True
            save = True

    if save:
        instance.save()


@receiver(post_save, sender=User)
def set_default_avatar(sender, instance: User, created, **kwargs):
    if created:
        if instance.avatar.name is None:
            with (
                settings.BASE_DIR / "fixtures" / "profile_pics" / "default.png"
            ).open("rb") as fp:
                django_file = ImageFile(file=fp, name="default.png")
                instance.avatar = django_file
                instance.save()


@receiver(post_save, sender=SMS2FA)
def send_otp_sms(sender, instance: SMS2FA, created, **kwargs):
    if created:
        send_sms_otp.delay(instance.pk)


@receiver(post_save, sender=Email2FA)
def send_otp_email(sender, instance: Email2FA, created, **kwargs):
    if created:
        send_email_otp.delay(instance.pk)
