# Generated by Django 4.0.10 on 2023-05-30 22:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sunrun', '0010_job_electrical_panel_file_job_receipt_file'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='photos',
        ),
        migrations.RemoveField(
            model_name='job',
            name='videos',
        ),
    ]