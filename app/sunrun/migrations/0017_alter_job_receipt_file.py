# Generated by Django 4.0.10 on 2023-05-30 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sunrun', '0016_alter_jobphoto_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='receipt_file',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
