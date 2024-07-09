import email
import logging
from email.message import Message

import boto3
from django.conf import settings

log = logging.getLogger(__name__)


class EmailLengthTooLarge(Exception):
    pass


class ObjectNotEmail(Exception):
    pass


class EmailClient:
    def __init__(
        self,
        s3_bucket: str = settings.FOLDER_EMAIL_S3_BUCKET,
        s3_bucket_prefix="",
        s3_client=None,
    ):
        self.s3_bucket_prefix = s3_bucket_prefix
        self.s3_bucket = s3_bucket
        if s3_client is None:
            _s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
        else:
            _s3_client = s3_client

        self.s3_paginator = _s3_client.get_paginator("list_objects_v2")
        self.s3_client = _s3_client

    def get_s3_content_pages(self):
        for page in self.s3_paginator.paginate(
            Bucket=self.s3_bucket, Prefix=self.s3_bucket_prefix
        ):
            contents = page.get("Contents")
            if contents:
                yield contents

    def get_email_content(self, s3_object_key: str) -> Message:
        obj = self.s3_client.get_object(
            Bucket=settings.FOLDER_EMAIL_S3_BUCKET, Key=s3_object_key
        )

        if obj["ContentLength"] < settings.FOLDER_EMAIL_MAX_LENGTH:
            body: bytes = obj["Body"].read()
            try:
                return email.message_from_bytes(body)
            except Exception:
                raise ObjectNotEmail(s3_object_key)

        else:
            raise EmailLengthTooLarge(obj["ContentLength"])
