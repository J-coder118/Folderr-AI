# Generated by Django 4.0.8 on 2022-12-18 20:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0029_alter_folderemail_s3_object_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='folderemail',
            name='s3_object_key',
            field=models.TextField(),
        ),
    ]
