# Generated by Django 4.0.10 on 2023-05-30 20:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sunrun', '0002_job_jobvideo_jobphoto_jobnote_job_notes_job_photos_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='notes',
        ),
    ]
