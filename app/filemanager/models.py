import datetime
import logging
import mimetypes
import secrets
import shutil
import string
import tempfile
import uuid
from functools import partial
from pathlib import Path

import html2text
import magic
import requests
from ckeditor.fields import RichTextField
from colorfield.fields import ColorField
from core.models import FileBaseModal, FolderBaseModel
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files import File as DjangoFile
from django.core.mail import send_mail
from django.db import IntegrityError, models, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from expenses.models import Expense
from recurrence.fields import RecurrenceField

from .tasks import convert_image_to_jpeg, generate_thumbnail_for_image

# Create your models here.
User = settings.AUTH_USER_MODEL

log = logging.getLogger(__name__)


class AssetType(models.Model):
    title = models.CharField(max_length=255)
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class SuggestedField(models.Model):
    title = models.CharField(max_length=255)
    placeholder = models.CharField(max_length=255)
    has_camera_access = models.BooleanField(default=False)
    asset_type = models.ForeignKey(
        AssetType, on_delete=models.CASCADE, related_name="suggested_field"
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["pk"]


class FolderType(models.Model):
    """Can be Assets or Records"""

    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class ZippedFolder(models.Model):
    zipped_at = models.DateTimeField(auto_now_add=True)
    folder = models.ForeignKey(
        "Folder", on_delete=models.CASCADE, related_name="zipped"
    )
    file = models.FileField()
    downloaded_at = models.DateTimeField(null=True, blank=True)


def folder_default_custom_fields():
    return {"Description": ""}


class FolderTransfer(models.Model):
    folder = models.OneToOneField(
        "Folder", on_delete=models.CASCADE, related_name="transfer"
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="transferred_folders",
        on_delete=models.CASCADE,
    )
    to_email = models.EmailField()
    claimed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def claim(self):
        previous_user = self.folder.created_by
        target_user = get_user_model().objects.get(email=self.to_email)
        self.folder.created_by = target_user
        self.folder.visible = True
        self.folder.visibility_reason = self.folder.UNKNOWN_VISIBILITY_REASON
        self.folder.save()
        self.claimed = True
        self.save()

        previous_user.reduce_disk_usage(self.folder.disk_usage_bytes)
        target_user.record_disk_usage(self.folder.disk_usage_bytes)
        log.info(
            "Folder %d was claimed by user %d", self.folder.id, target_user.id
        )

    def send_email(self):
        ctx = {
            "user": self.from_user,
            "cta_url": f"{settings.FRONT_END_URL}/claim-folder/{self.folder.pk}/",
        }
        message_txt = render_to_string(
            "filemanager/emails/folder-transfer.txt", ctx
        )
        message_html = render_to_string(
            "filemanager/emails/folder-transfer.html", ctx
        )
        send_mail(
            subject="Claim your folder",
            message=message_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.to_email],
            html_message=message_html,
        )

    @property
    def claim_display(self):
        if self.claimed:
            return "Claimed"
        return "Unclaimed"

    def __str__(self):
        return f"Folder transferred from {self.from_user.email} to {self.to_email} ({self.claim_display})"


class Folder(FolderBaseModel):
    TRANSFERRED_VISIBILITY_REASON = 0
    UNKNOWN_VISIBILITY_REASON = 1
    VISIBILITY_CHOICES = (
        (TRANSFERRED_VISIBILITY_REASON, "Transferred"),
        (UNKNOWN_VISIBILITY_REASON, "Unknown"),
    )
    title = models.CharField(max_length=100, blank=False, null=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subfolders",
    )
    is_root = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    folder_type = models.ForeignKey(
        FolderType, on_delete=models.CASCADE, default=1
    )
    asset_type = models.ForeignKey(
        AssetType, on_delete=models.CASCADE, null=True, blank=True
    )
    custom_fields = models.JSONField(
        "FolderCustomFields", default=folder_default_custom_fields
    )
    email = models.EmailField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True)
    visible = models.BooleanField(default=True)
    visibility_reason = models.PositiveSmallIntegerField(
        default=UNKNOWN_VISIBILITY_REASON, choices=VISIBILITY_CHOICES
    )

    disk_usage_bytes = models.BigIntegerField(default=0)

    def set_email(self):
        sequence = "".join(secrets.choice(string.digits) for _ in range(6))
        email = f"{sequence}@{settings.FOLDER_EMAIL_DOMAIN}"
        try:
            Folder.objects.get(email=email)
            return self.set_email()
        except Folder.DoesNotExist:
            self.email = email

    @property
    def full_address(self):
        return (
            f"{self.custom_fields.get('Address')}, "
            f"{self.custom_fields.get('City')}, {self.custom_fields.get('State')}, "
            f"{self.custom_fields.get('ZIP')}"
        )

    def save(self, *args, **kwargs):
        # A root folder cannot have a parent folder.
        # If parent is specified, then it is not a root folder.
        self.is_root = not bool(self.parent)
        super(Folder, self).save(*args, **kwargs)

    def _save_folder_files(self, folder, path: Path):
        for file in folder.files.all():
            file_path = path / file.file_name
            with file_path.open("wb") as fp:
                for chunk in file.file.chunks():
                    fp.write(chunk)

    def _save_folder_videos(self, folder, path):
        for video in folder.video_files.all():
            file_path = path / video.title
            with file_path.open("wb") as fp:
                for chunk in video.file.chunks():
                    fp.write(chunk)

    def _save_folder_notes(self, folder, path: Path):
        for note in folder.stickynotes.all():
            note_path = path / f"{secrets.token_urlsafe()}.txt"
            with note_path.open("w", encoding="utf-8") as fp:
                fp.write(html2text.html2text(note.description))

    def _save_folder_tasks(self, folder, path: Path):
        for task in folder.task.all():
            task_path = path / f"{task.title}.txt"
            with task_path.open("w", encoding="utf-8") as fp:
                fp.write(f"Start at: {task.start_at}\n")
                fp.write(f"End at: {task.end_at}\n")
                fp.write(f"Remind at: {task.remind_at}\n")
                fp.write(f"Done: {task.done}\n\n\n")
                fp.write(task.description)

    def zip_contents(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            folder_path = Path(tmp_dir)
            if self.is_root:
                for subfolder in self.subfolders.all():
                    subfolder_path: Path = folder_path / subfolder.title
                    subfolder_path.mkdir(exist_ok=True)
                    self._save_folder_files(subfolder, subfolder_path)
                    self._save_folder_videos(subfolder, subfolder_path)
                    self._save_folder_notes(subfolder, subfolder_path)
                    self._save_folder_tasks(subfolder, subfolder_path)
            self._save_folder_files(self, folder_path)
            self._save_folder_videos(self, folder_path)
            self._save_folder_notes(self, folder_path)
            self._save_folder_tasks(self, folder_path)
            zip_basename = str(
                Path(tempfile.gettempdir()) / slugify(self.title)
            )
            zip_filepath = zip_basename + ".zip"
            shutil.make_archive(
                zip_basename, "zip", root_dir=tmp_dir, base_dir=tmp_dir
            )
            log.info(
                "Created zip archive for folder %d at %s",
                self.pk,
                folder_path / zip_filepath,
            )
            with (folder_path / zip_filepath).open("rb") as fp:
                file_name = Path(zip_filepath).name
                django_file = DjangoFile(fp, name=file_name)
                zipped_folder = ZippedFolder(folder=self, file=django_file)
                zipped_folder.save()
                return zipped_folder.pk

    def transfer_to_email(self, to_email):
        if hasattr(self, "transfer"):
            transfer = self.transfer
            transfer.from_user = self.created_by
            transfer.to_email = to_email
            transfer.claimed = False
        else:
            transfer = FolderTransfer(
                folder=self, from_user=self.created_by, to_email=to_email
            )
        transfer.save()
        self.visible = False
        self.visibility_reason = self.TRANSFERRED_VISIBILITY_REASON
        self.save()
        return transfer

    def cancel_transfer(self):
        if hasattr(self, "transfer"):
            self.transfer.delete()
            self.visible = True
            self.save()

    def update_disk_usage(self, action: str, file_size_bytes: int):
        if self.is_root:
            obj = self
        else:
            obj = self.parent

        if action == "add":
            obj.disk_usage_bytes += file_size_bytes
        elif action == "reduce":
            obj.disk_usage_bytes -= file_size_bytes
        else:
            raise ValueError(f"Unknown action {action}.")
        obj.save()

    def __str__(self):
        return self.title


class File(FileBaseModal):
    def upload_file_to(instance, filename):
        """
        INSTANCE
        {'_state': <django.db.models.base.ModelState object at 0x7fb9c150e200>,
        'created': datetime.datetime(2022, 7, 6, 0, 48, 42, 689682, tzinfo=datetime.timezone.utc),
        'created_by_id': 1,
        'file': <FieldFile: sample (1).pdf>,
        'folder_id': 2,
        'id': UUID('81b15219-6419-4ed1-b477-31cab90ef509'),
        'updated': datetime.datetime(2022, 7, 6, 0, 48, 42, 689715, tzinfo=datetime.timezone.utc)}
        FILENAME: sample (1).pdf
        """
        return f"files/{instance.created_by_id}/{str(instance.id)}/{filename}"

    file_name = models.CharField(max_length=1000)
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(upload_to=upload_file_to, blank=False, null=False)
    thumbnail = models.ImageField(
        upload_to="thumbnails", null=True, blank=True
    )
    quality_score = models.FloatField(null=True, blank=True)
    _mime_type = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"File {self.file_name} (Folder {self.folder.id})"

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
        generate_thumbnail=True,
    ):
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
        if generate_thumbnail:
            transaction.on_commit(
                partial(generate_thumbnail_for_image, self.pk)
            )
        transaction.on_commit(partial(convert_image_to_jpeg, self.pk))

    def set_mime_type(self):
        with tempfile.NamedTemporaryFile("wb+") as fp:
            for chunk in self.file.chunks():
                fp.write(chunk)
            fp.seek(0)
            mime = magic.from_buffer(fp.read(), mime=True)
            self._mime_type = mime
            self.save()
        return mime

    @property
    def mime_type(self):
        if self._mime_type:
            return self._mime_type
        return self.set_mime_type()

    def save_ocr_data(self, ocr_data: dict) -> tuple[bool, list, Expense]:
        errors = []
        if getattr(self, "expense", None) is not None:
            instance = self.expense
        else:
            instance = Expense(file=self)
        summary = {}
        for field_name, field_value in ocr_data["summary_fields"].items():
            log.debug("Adding field %s with value %s", field_name, field_value)
            summary[field_name.lower()] = field_value
        instance.summary = summary

        line_items = []
        for line_data in ocr_data["line_item_fields"]:
            if isinstance(line_data, dict):
                log.debug("Creating line item from %s", line_data)
                line_items.append(line_data)
        instance.line_items = line_items
        instance.save()

        try:
            instance.full_clean()
            instance.save()
        except ValidationError as e:
            log.info("OCR data %s isn't valid", ocr_data)
            errors.append(f"Invalid fields found: {e.message_dict}")
        except IntegrityError as e:
            log.info(
                "IntegrityError %s while saving Expense for file %d.",
                e,
                instance.file.pk,
            )
            errors.append(
                "An unknown error occurred while saving this data. Please try again or contact us."
            )

        success = len(errors) == 0
        return success, errors, instance

    @property
    def is_image(self):
        guess, _ = mimetypes.guess_type(self.file.name)

        if guess is None:
            return False

        if "image" in guess:
            return True
        return False

    def update_quality_score(self) -> bool:
        with tempfile.NamedTemporaryFile("wb+") as fp:
            for chunk in self.file.chunks():
                fp.write(chunk)
            fp.seek(0)
            request_params = {
                "models": "quality",
                "api_user": settings.IMAGE_QUALITY_API_USER,
                "api_secret": settings.IMAGE_QUALITY_API_SECRET,
            }
            try:
                response = requests.post(
                    "https://api.sightengine.com/1.0/check.json",
                    data=request_params,
                    files={"media": fp},
                )
                data = response.json()
                score = data["quality"]["score"]
                self.quality_score = score
                self.save()
                return True
            except Exception as e:
                log.exception(e)
            return False


class SuggestedFolder(models.Model):
    title = models.CharField(max_length=255)
    asset_type = models.ForeignKey(
        AssetType, on_delete=models.CASCADE, related_name="suggested_folder"
    )

    def __str__(self) -> str:
        return self.title


class IgnoredSuggestedFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    suggested_folder = models.ForeignKey(
        SuggestedFolder, on_delete=models.CASCADE, related_name="as_ignored"
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="ignored_suggested_folders",
    )
    ignored_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.suggested_folder.title} ignored by {self.user}"

    class Meta:
        db_table = "ignored_suggested_folders"


class Comment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, null=True, blank=True
    )
    file = models.ForeignKey(
        File, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self) -> str:
        return super().__str__()


# class UserActivity(models.Model):
#     ACTION_CHOICES = (
#         (1, "FILE_ADD"),
#         (2, "FILE_EDIT"),
#         (3, "FILE_DELETE"),
#         (4, "FOLDER_ADD"),
#         (5, "FOLDER_EDIT"),
#         (6, "FOLDER_DELETE"),
#         (7, "COMMENT_ADD"),
#         (8, "COMMENT_EDIT"),
#         (9, "COMMENT_DELETE"),
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     action = models.CharField(max_length=100, choices=ACTION_CHOICES)
#     file = models.ForeignKey(
#         File,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="file_activty",
#     )
#     folder = models.ForeignKey(
#         Folder,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="folder_activity",
#     )
#     comment = models.ForeignKey(
#         Comment,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="comment_activity",
#     )
#
#     def __str__(self):
#         return f"{self.id}"


class StickyNote(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=500, blank=False, null=False)
    short_description = models.CharField(max_length=150, blank=True, null=True)
    color = models.CharField(max_length=10, blank=False, null=False)
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name="stickynotes"
    )


class Share(models.Model):
    PERMISSION_CHOICES = (
        (1, "CO-OWNER"),
        (2, "CONTRIBUTER"),
        (3, "VIEW ONLY"),
    )
    created = models.DateTimeField(auto_now_add=True)
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name="shared_with"
    )
    permission = models.CharField(max_length=100, choices=PERMISSION_CHOICES)
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sender"
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="receiver",
        null=True,
        blank=True,
    )
    receiver_email = models.EmailField(max_length=256, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.sender} share to {self.receiver} {self.id}"


class ShareNotification(models.Model):
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="notifications"
    )
    content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "share_notifications"
        ordering = ["-updated_at"]


class TaskReminder(models.Model):
    task = models.OneToOneField(
        "Task", on_delete=models.CASCADE, related_name="reminder"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "task_reminders"
        ordering = ["-updated_at"]


class Task(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=100)
    due_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    recurrences = RecurrenceField(null=True, blank=True)
    remind_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    done = models.BooleanField(default=False)
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name="task"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    was_repeated = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.title}"

    def repeat_task(self):
        if self.recurrences is not None:
            if not self.was_repeated:
                if self.remind_at is not None:
                    after_date = self.remind_at
                else:
                    after_date = timezone.now()

                next_occurrence = self.recurrences.after(
                    after_date, dtstart=self.due_at, dtend=self.end_at
                )

                if next_occurrence is not None:
                    occurrence_time_delta = next_occurrence - after_date

                    if self.remind_at is not None:
                        required_time_delta = occurrence_time_delta
                    else:
                        required_time_delta = datetime.timedelta(days=7)

                    if (after_date + required_time_delta) > next_occurrence:
                        task = Task(
                            title=self.title,
                            start_at=next_occurrence,
                            end_at=self.end_at,
                            recurrences=self.recurrences,
                            description=self.description,
                            folder=self.folder,
                            created_by=self.created_by,
                        )
                        if self.remind_at is not None:
                            time_until_start = self.due_at - self.remind_at
                            task.remind_at = task.due_at - time_until_start
                        task.full_clean()
                        task.save()
                        self.was_repeated = True
                        self.save()
                        log.info(
                            "Task %d was repeated. New task: %d",
                            self.pk,
                            task.pk,
                        )

    def should_remind(self):
        if not hasattr(self, "reminder"):
            if not self.done:
                if self.remind_at:
                    return self.remind_at < timezone.now()
        return False

    def create_reminder(self):
        reminder = TaskReminder(task=self)
        reminder.save()
        return reminder


def upload_video_to(instance, filename):
    now = datetime.datetime.now()
    return f"files/{instance.folder.created_by_id}/videos/{now.strftime('%Y-%m-%d')}-{secrets.token_urlsafe(1)}/{filename}"


class VideoFile(models.Model):
    PROCESSING = 0
    READY = 1
    STATUS_CHOICES = ((PROCESSING, "Processing"), (READY, "Ready"))
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name="video_files"
    )
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to=upload_video_to)
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PROCESSING
    )
    thumbnail = models.ImageField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.file.name} ({self.get_status_display()})"

    class Meta:
        db_table = "video_files"


class DefaultNote(models.Model):
    asset_type = models.ForeignKey(
        AssetType, on_delete=models.CASCADE, related_name="default_notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=100, blank=False, null=False)
    description = RichTextField()
    short_description = models.CharField(
        max_length=150, blank=True, null=True, editable=False
    )
    color = ColorField(default="#FF0000")

    def __str__(self):
        return self.title

    class Meta:
        db_table = "default_notes"
        ordering = ["-updated_at"]


class SharedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.TextField()
    content_object = GenericForeignKey()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shared_files"
        ordering = ["-updated_at"]


class SharedFileEmail(models.Model):
    shared_file = models.ForeignKey(
        SharedFile, on_delete=models.CASCADE, related_name="emails"
    )
    email = models.EmailField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def send_email(self):
        ctx = {
            "user": self.shared_file.content_object.folder.created_by,
            "share_url": f"{settings.FRONT_END_URL}/shared-file/{self.pk}/",
        }
        message = render_to_string("filemanager/emails/file-share.txt", ctx)
        html_message = render_to_string(
            "filemanager/emails/file-share.html", ctx
        )
        send_mail(
            "A file was shared with you",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [self.email],
            html_message=html_message,
        )

    class Meta:
        db_table = "shared_file_emails"
        ordering = ["-updated_at"]
