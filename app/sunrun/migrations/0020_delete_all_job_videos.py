# Generated by Django 4.0.10 on 2023-05-30 22:18

from django.db import migrations


def delete_all_job_videos(apps, schema_editor):
    JobVideo = apps.get_model('sunrun', 'JobVideo')
    JobVideo.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('sunrun', '0019_jobvideo_video'),
    ]

    operations = [
        migrations.RunPython(delete_all_job_videos, migrations.RunPython.noop)
    ]