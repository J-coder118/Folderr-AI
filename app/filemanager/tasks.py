import logging
import secrets
import subprocess
import tempfile
from pathlib import Path

import magic
from celery import shared_task
from django.apps import apps
from django.core.files import File as DjangoFile
from django.core.files.images import ImageFile
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
# from preview_generator.manager import PreviewManager

log = logging.getLogger(__name__)

register_heif_opener()


@shared_task
def generate_thumbnail_for_image(image_pk):
    File = apps.get_model("filemanager", "File")
    image_file = File.objects.get(pk=image_pk)
    _, tmp_file = tempfile.mkstemp()
    _, tmp_thumb = tempfile.mkstemp(suffix=".jpg")
    with Path(tmp_file).open("wb") as fp:
        for chunk in image_file.file.chunks():
            fp.write(chunk)

    mime_type = magic.from_file(tmp_file, mime=True)
    file_type, extension = mime_type.split("/")
    log.debug("Received file type %s with extension %s", file_type, extension)
    if file_type == "image":
        with Image.open(tmp_file) as pil_image:
            thumbnail_image = ImageOps.exif_transpose(pil_image)
            thumbnail_image.thumbnail((500, 500))

            thumbnail_image = thumbnail_image.convert("RGB")

            thumbnail_image.save(tmp_thumb, format="JPEG")
            thumbnail_image.seek(0)

            with Path(tmp_thumb).open("rb") as fp:
                django_file = ImageFile(
                    file=fp, name=f"{secrets.token_urlsafe()}.jpg"
                )
                image_file.thumbnail = django_file
                image_file.save(generate_thumbnail=False)
    elif extension == "pdf":
        cache_path = tempfile.mkdtemp()
        # manager = PreviewManager(cache_path, create_folder=True)
        # pdf_preview_path = manager.get_jpeg_preview(tmp_file)
        # with Path(pdf_preview_path).open("rb") as fp:
        #     django_file = ImageFile(
        #         file=fp, name=f"{secrets.token_urlsafe()}.jpg"
        #     )
        #     image_file.thumbnail = django_file
        #     image_file.save(generate_thumbnail=False)


@shared_task
def convert_image_to_jpeg(file_pk):
    File = apps.get_model("filemanager", "File")
    file = File.objects.get(pk=file_pk)
    _, tmp_file = tempfile.mkstemp()
    with tempfile.NamedTemporaryFile("wb+") as tmp_file:
        for chunk in file.file.chunks():
            tmp_file.write(chunk)

        tmp_file.seek(0)

        mime_type = magic.from_buffer(tmp_file.read(2048), mime=True)
        file_type, extension = mime_type.split("/")
        tmp_file.seek(0)
        if file_type == "image":
            if extension == "heic":
                with Image.open(
                    tmp_file
                ) as pil_image, tempfile.NamedTemporaryFile("wb+") as tmp_jpeg:
                    pil_image.save(tmp_jpeg, format="JPEG")
                    tmp_jpeg.seek(0)
                    file_name, _ = file.file_name.split(".")
                    django_file = DjangoFile(
                        file=tmp_jpeg, name=f"{file_name}.jpg"
                    )
                    file.file = django_file
                    file.file_name = file_name + ".jpg"
                    file.save(generate_thumbnail=False)


@shared_task
def generate_thumbnail_for_video(video_pk):
    VideoFile = apps.get_model("filemanager", "VideoFile")
    video_file = VideoFile.objects.get(pk=video_pk)
    _, tmp_file = tempfile.mkstemp()
    with Path(tmp_file).open("wb") as fp:
        for chunk in video_file.file.chunks():
            fp.write(chunk)

    _, img_path = tempfile.mkstemp(suffix=".jpg")
    subprocess.call(
        [
            "ffmpeg",
            "-i",
            tmp_file,
            "-ss",
            "00:00:00.000",
            "-vframes",
            "1",
            "-y",
            img_path,
        ]
    )
    with Path(img_path).open("rb") as fp:
        django_file = ImageFile(
            file=fp, name=f"{video_file.title}-thumbnail.jpg"
        )
        video_file.thumbnail = django_file
        video_file.save()


@shared_task
def zip_folder_contents(folder_id: int):
    Folder = apps.get_model("filemanager", "Folder")
    try:
        folder = Folder.objects.get(pk=folder_id)
    except Folder.DoesNotExist:
        log.info("Folder %d doesn't exist.", folder_id)
        return
    return folder.zip_contents()


@shared_task
def send_shared_file_email(shared_file_email_pk):
    SharedFileEmail = apps.get_model("filemanager", "SharedFileEmail")
    shared_file_email = SharedFileEmail.objects.get(pk=shared_file_email_pk)
    shared_file_email.send_email()


@shared_task
def send_folder_transfer_email(folder_transfer_pk):
    FolderTransfer = apps.get_model("filemanager", "FolderTransfer")
    folder_transfer = FolderTransfer.objects.get(pk=folder_transfer_pk)
    if folder_transfer.claimed is False:
        folder_transfer.send_email()
