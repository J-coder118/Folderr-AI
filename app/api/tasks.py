import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger(__name__)


@shared_task
def contact_us(payload):
    send_mail(
        subject="New User Inquiry",
        message=f"Name: {payload['name']} Email: {payload['email']} Message: {payload['msg']}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=settings.EMAIL_RECIPIENT_LIST,
    )
    log.info("Contact us email sent.")
