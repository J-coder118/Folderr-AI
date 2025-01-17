# Generated by Django 4.0.10 on 2023-05-30 22:14

from django.db import migrations


def delete_all_job_photos(apps, schema_editor):
    JobPhoto = apps.get_model('sunrun', 'JobPhoto')
    JobPhoto.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('sunrun', '0014_jobphoto_file'),
    ]

    operations = [
        migrations.RunPython(delete_all_job_photos, migrations.RunPython.noop)
    ]
