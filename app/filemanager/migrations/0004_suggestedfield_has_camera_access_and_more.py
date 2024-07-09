# Generated by Django 4.0.4 on 2022-07-14 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0003_remove_assettype_suggested_field_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='suggestedfield',
            name='has_camera_access',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='suggestedfield',
            name='placeholder',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]