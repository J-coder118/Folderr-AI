# Generated by Django 4.0.8 on 2022-12-18 00:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0025_videofile_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='folder',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
