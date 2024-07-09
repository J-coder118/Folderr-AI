import logging
import tempfile

from core.models import FolderrEmail
from django.core.files import File as DjangoFile
from filemanager.models import File
from html2text import html2text

log = logging.getLogger(__name__)


def html_body_to_text(body: str) -> str:
    return html2text(body)


def process_email(pk: int, force=False):
    folderr_email = FolderrEmail.objects.get(pk=pk)
    log.info("Processing FolderrEmail %d", pk)
    if folderr_email.status == folderr_email.PROCESSING and force is False:
        for attachment in folderr_email.attachments.all():
            with tempfile.NamedTemporaryFile("wb+") as file_fp:
                for chunk in attachment.file.chunks():
                    file_fp.write(chunk)
                file_fp.seek(0)
                django_file = DjangoFile(file=file_fp, name=attachment.title)
                file = File.objects.create(
                    file_name=attachment.title,
                    folder=folderr_email.asset,
                    file=django_file,
                    created_by=folderr_email.user,
                )
                log.info(
                    "Created file %d from attachment %d",
                    file.pk,
                    attachment.pk,
                )
        folderr_email.status = folderr_email.PROCESSED
        folderr_email.save()
    else:
        log.info("FolderrEmail %d was already processed.", folderr_email.pk)
