# Generated by Django 4.0.10 on 2023-05-30 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sunrun', '0020_delete_all_job_videos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobvideo',
            name='video',
            field=models.FileField(upload_to=''),
        ),
    ]
