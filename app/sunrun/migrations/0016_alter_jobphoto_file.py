# Generated by Django 4.0.10 on 2023-05-30 22:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sunrun', '0015_delete_all_job_photos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobphoto',
            name='file',
            field=models.ImageField(upload_to=''),
        ),
    ]
