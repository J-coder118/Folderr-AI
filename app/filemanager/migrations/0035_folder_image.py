# Generated by Django 4.0.8 on 2022-12-23 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0034_delete_folderemail'),
    ]

    operations = [
        migrations.AddField(
            model_name='folder',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]