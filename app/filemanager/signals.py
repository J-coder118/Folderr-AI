import logging
from functools import partial

import bleach
import html2text
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from filemanager.models import (
    AssetType,
    File,
    Folder,
    FolderTransfer,
    Share,
    SharedFileEmail,
    ShareNotification,
    StickyNote,
    Task,
    VideoFile,
)
from filemanager.tasks import (
    generate_thumbnail_for_video,
    send_folder_transfer_email,
    send_shared_file_email,
)

log = logging.getLogger("filemanager.signals")


# @receiver(post_save, sender=Folder)
# def folder_signal(sender, instance, created, **kwargs):
#     if created:
#         action = {"action": 4}
#     else:
#         action = {"action": 5}
#     UserActivity.objects.create(
#         folder=instance, user=instance.created_by, **action
#     )


@receiver(post_save, sender=Folder)
def set_folder_email_address(sender, instance, created, **kwargs):
    if created:
        instance.set_email()
        instance.save()


@receiver(post_save, sender=File)
def populate_mime_type_on_create(sender, instance, created, **kwargs):
    if created:
        instance.set_mime_type()


# @receiver(post_save, sender=File)
# def file_signal(sender, instance, created, **kwargs):
#     if created:
#         action = {"action": 1}
#     else:
#         action = {"action": 2}
#     UserActivity.objects.create(
#         file=instance,
#         folder=instance.folder,
#         user=instance.created_by,
#         **action,
#     )


# @receiver(post_save, sender=Comment)
# def comment_signal(sender, instance, created, **kwargs):
#     if created:
#         action = {"action": 7}
#
#     else:
#         action = {"action": 8}
#     UserActivity.objects.create(user=instance.user, comment=instance, **action)


@receiver(post_save, sender=Share)
def create_notification_on_create(sender, instance, created, **kwargs):
    if created:
        content = {
            "title": "New shared folder",
            "level": "success",
            "message": f"{instance.sender.email} shared a folder with you.",
        }
        ShareNotification.objects.create(share=instance, content=content)


@receiver(post_save, sender=VideoFile)
def create_thumbnail_in_background(sender, instance, created, **kwargs):
    if created:
        generate_thumbnail_for_video.delay(instance.pk)


@receiver(post_save, sender=VideoFile)
def record_user_disk_usage_for_video_files(
    sender, instance, created, **kwargs
):
    if created:
        user = instance.folder.created_by
        file_size = instance.file.size
        user.record_disk_usage(file_size)
        instance.folder.update_disk_usage("add", instance.file.size)


@receiver(post_delete, sender=VideoFile)
def reduce_user_disk_usage_on_video_delete(sender, instance, **kwargs):
    user = instance.folder.created_by
    file_size = instance.file.size
    user.reduce_disk_usage(file_size)
    instance.folder.update_disk_usage("reduce", instance.file.size)


@receiver(post_save, sender=File)
def record_user_disk_usage_for_files(sender, instance, created, **kwargs):
    if created:
        user = instance.created_by
        file_size = instance.file.size
        user.record_disk_usage(file_size)
        instance.folder.update_disk_usage("add", instance.file.size)


@receiver(post_delete, sender=File)
def reduce_user_disk_usage_on_file_delete(sender, instance, **kwargs):
    user = instance.created_by
    file_size = instance.file.size
    user.reduce_disk_usage(file_size)
    instance.folder.update_disk_usage("reduce", instance.file.size)


@receiver(pre_save, sender=StickyNote)
def generate_short_description(sender, instance, *args, **kwargs):
    instance.short_description = html2text.html2text(instance.description)[
        :140
    ]


@receiver(pre_save, sender=StickyNote)
def sanitize_note_description(sender, instance: StickyNote, *args, **kwargs):
    instance.description = bleach.clean(
        instance.description,
        tags=list(bleach.sanitizer.ALLOWED_TAGS) + ["p", "br"],
    )


@receiver(post_save, sender=Folder)
def create_default_notes(sender, instance: Folder, created, *args, **kwargs):
    if created:
        for default_note in instance.asset_type.default_notes.all():
            sticky_note = StickyNote(
                created_by=instance.created_by,
                title=default_note.title,
                description=default_note.description,
                color=default_note.color,
                folder=instance,
            )
            sticky_note.save()


@receiver(post_save, sender=Task)
def delete_task_reminder(sender, instance: Task, created, *args, **kwargs):
    to_delete = False
    if hasattr(instance, "reminder"):
        if instance.remind_at is None:
            to_delete = True
        elif instance.done:
            to_delete = True
    if to_delete:
        instance.reminder.delete()


@receiver(post_save, sender=SharedFileEmail)
def send_email_on_create(sender, instance, created, *args, **kwargs):
    if created:
        send_shared_file_email.delay(instance.pk)


@receiver(post_save, sender=FolderTransfer)
def send_folder_transfer_email_signal(
    sender, instance, created, *args, **kwargs
):
    transaction.on_commit(
        partial(send_folder_transfer_email.delay, instance.pk)
    )


@receiver(post_save, sender=Folder)
def create_ai_subfolder_on_create(sender, instance, created, *args, **kwargs):
    if created:
        if instance.is_root:
            log.info("Will create AI folder for new asset %d.", instance.pk)
            ai_asset_type = AssetType.objects.get(title="AI")
            ai_subfolder = Folder(
                created_by=instance.created_by,
                title="AI",
                parent=instance,
                is_root=False,
                asset_type=ai_asset_type,
            )
            ai_subfolder.full_clean()
            ai_subfolder.save()
