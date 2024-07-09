from __future__ import absolute_import, unicode_literals

import logging
import secrets
import time
from io import BytesIO

import boto3
from celery import shared_task
from core.email import process_email
from core.models import SMS2FA, Email2FA, FolderrEmail, FolderrEmailAttachment
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.mail import send_mail
from django.template.loader import render_to_string
from filemanager.email import EmailClient
from filemanager.models import Folder

log = logging.getLogger(__name__)

User = get_user_model()


@shared_task
def add_two_numbers(x, y):
    print("***************** CELERY TASK *****************")
    print(f"X: {x}")
    print(f"Y: {y}")
    print(f"Sum: {x + y}")
    return x + y


@shared_task
def send_email(
    subject,
    body,
    sender,
    recipients,
    fail_silently,
    html_body="",
    button_link="",
):
    print("***************** SEND MAIL  *****************")
    print("Recipients: {recipients}")
    try:
        if html_body:
            html_message = render_to_string(
                "folder-share.html",
                {"html_text": html_body, "button_link": button_link},
            )
            sent = send_mail(
                subject=subject,
                message=body,
                from_email=sender,
                recipient_list=recipients,
                fail_silently=fail_silently,
                html_message=html_message,
            )
        else:
            sent = send_mail(
                subject=subject,
                message=body,
                from_email=sender,
                recipient_list=recipients,
                fail_silently=fail_silently,
            )
        print("response", sent)
        print("Please check your inbox.")
    except Exception as e:
        print(f"Error: {str(e)}")


@shared_task
def task_otp_for_password_reset(phone_number, sms_body):
    print("***************** SEND SMS - PASSWORD RESET *****************")
    print("Recipient: {phone_number}")
    try:
        sns = boto3.client(
            "sns",
            aws_access_key_id=settings.AWS_SNS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SNS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_SNS_REGION_NAME,
        )
        sns.publish(PhoneNumber=phone_number, Message=sms_body)
        print("OTP Sent.")
    except Exception as e:
        print(f"Error : {e}")


@shared_task
def process_folderr_email(pk):
    folderr_email = FolderrEmail.objects.get(pk=pk)
    folderr_email.process_email()


@shared_task
def fetch_mail_from_s3(object_key: str):
    log.info("Attempting to fetch email from %s", object_key)
    email_client = EmailClient()
    email_content = email_client.get_email_content(object_key)
    from_address = email_content.get("From", "")
    subject = email_content.get("Subject", "")
    destination = email_content["To"]
    log.debug(
        "Got email from %s with subject %s destined to %s",
        from_address,
        subject,
        destination,
    )
    try:
        asset = Folder.objects.get(email=destination)
        log.info("Email is destined to asset %d", asset.pk)
    except Folder.DoesNotExist:
        log.info(
            "User with folderr email %s doesn't exist. Object key: %s.",
            destination,
            object_key,
        )
        return
    user = asset.created_by
    if user.can_receive_email:
        folderr_email = FolderrEmail.objects.create(
            user=user,
            asset=asset,
            s3_object_key=object_key,
            email_from=from_address,
            email_subject=subject,
        )
        if not user.is_plus:
            user.record_email_receipt()
        log.info("Created FolderrEmail %d", folderr_email.pk)
        message_body = ""
        message_body_html = ""
        for part in email_content.walk():
            main_type = part.get_content_maintype()
            sub_type = part.get_content_subtype()
            log.debug("Got part %s/%s", main_type, sub_type)
            payload: bytes = part.get_payload(decode=True)
            if main_type == "text":
                decoded_payload = payload.decode("utf-8")
                if sub_type == "plain":
                    message_body += decoded_payload
                elif sub_type == "html":
                    message_body_html += decoded_payload
            elif (is_image := main_type == "image") or (
                main_type == "application" and "pdf" in sub_type
            ):
                log.debug(
                    "Main type is %s and is_image is %s", main_type, is_image
                )
                file_name = part.get_filename(
                    failobj=f"{secrets.token_urlsafe()}.{sub_type}"
                )
                django_file = File(file=BytesIO(payload), name=file_name)
                attachment = FolderrEmailAttachment.objects.create(
                    email=folderr_email,
                    title=file_name,
                    file=django_file,
                    is_image=is_image,
                )
                log.info("Created attachment %d", attachment.pk)
        folderr_email.email_message = message_body
        folderr_email.email_message_html = message_body_html
        folderr_email.save()
        process_email(folderr_email.pk)
    else:
        log.info("User %d isn't allowed to receive any more emails", user.pk)


@shared_task
def process_email_task(pk):
    log.debug("Processing email for %s", pk)
    email = FolderrEmail.objects.get(pk=pk)
    retry_count = 0
    while retry_count < 10:
        if email.status == email.PROCESSING:
            break
        time.sleep(1)
        email.refresh_from_db()
        retry_count += 1

    process_email(pk)


@shared_task
def send_sms_otp(pk):
    tries = 0
    while tries < 10:
        try:
            sms = SMS2FA.objects.get(pk=pk)
        except SMS2FA.DoesNotExist:
            tries += 1
            continue
        sms.send_sms()
        break


@shared_task
def send_email_otp(pk):
    tries = 0
    while tries < 10:
        try:
            email = Email2FA.objects.get(pk=pk)
        except Email2FA.DoesNotExist:
            tries += 1
            continue
        email.send_email()
        break
