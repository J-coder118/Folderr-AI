# Generated by Django 4.0.10 on 2023-05-30 22:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sunrun', '0012_alter_jobphoto_job_alter_jobvideo_job'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jobphoto',
            name='file',
        ),
    ]