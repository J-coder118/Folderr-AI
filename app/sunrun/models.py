from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Checklist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sunrun_checklists",
    )
    name = models.CharField(max_length=255)
    requirements = models.JSONField()
    add_photo = models.BooleanField()
    add_video = models.BooleanField()
    add_note = models.BooleanField()
    scan_electrical_panel = models.BooleanField()
    scan_receipt = models.BooleanField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sunrun_checklists"
        ordering = ["-updated_at"]


class Job(models.Model):
    checklist = models.ForeignKey(
        Checklist, on_delete=models.CASCADE, related_name="jobs"
    )
    checked_requirements = models.JSONField(default=list)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sunrun_jobs",
    )
    full_address = models.CharField(max_length=255)
    address_city = models.CharField(max_length=255)
    address_state = models.CharField(max_length=50)
    address_zip = models.CharField(max_length=40)
    receipt_file = models.ImageField(null=True, blank=True)
    electrical_panel_file = models.ImageField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sunrun_jobs"
        ordering = ["-updated_at"]


def upload_photo_to(instance, filename):
    return f"sunrun/jobs/{instance.job.id}/{slugify(filename)}"


class JobPhoto(models.Model):
    file = models.FileField(upload_to=upload_photo_to)
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="photos"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sunrun_job_photos"
        ordering = ["-updated_at"]


class JobVideo(models.Model):
    video = models.FileField()
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="videos"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sunrun_job_videos"
        ordering = ["-updated_at"]


class JobNote(models.Model):
    description = models.CharField(max_length=10000)
    color = models.CharField(max_length=150)
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="notes"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sunrun_job_notes"
        ordering = ["-updated_at"]
