# Generated by Django 4.0.8 on 2022-12-18 00:12

from django.db import migrations


def forward(apps, schema_editor):
    pass
    # from filemanager.models import Folder
    # for folder in Folder.objects.all():
    #     folder.set_email()
    #     folder.save()


class Migration(migrations.Migration):
    dependencies = [
        ('filemanager', '0026_folder_email'),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop)
    ]
