# Generated by Django 4.0.10 on 2023-08-22 19:35

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("filemanager", "0062_create_ai_subfolder"),
    ]

    operations = [
        migrations.DeleteModel(
            name="UserActivity",
        ),
    ]
