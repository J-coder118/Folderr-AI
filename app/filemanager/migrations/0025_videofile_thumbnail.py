# Generated by Django 4.0.8 on 2022-12-16 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0024_videofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='videofile',
            name='thumbnail',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
