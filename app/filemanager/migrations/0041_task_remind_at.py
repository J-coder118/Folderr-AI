# Generated by Django 4.0.8 on 2023-01-01 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0040_alter_task_start_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='remind_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
