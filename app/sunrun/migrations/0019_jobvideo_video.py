# Generated by Django 4.0.10 on 2023-05-30 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sunrun', '0018_remove_jobvideo_video'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobvideo',
            name='video',
            field=models.FileField(blank=True, null=True, upload_to=''),
        ),
    ]
