# Generated by Django 4.0.10 on 2023-03-15 21:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0050_task_reminder_dismissed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stickynote',
            name='pin',
        ),
    ]