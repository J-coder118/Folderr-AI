# Generated by Django 4.0.8 on 2022-12-22 16:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('help', '0002_helptopicimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='helptopic',
            name='order',
            field=models.SmallIntegerField(default=0, help_text='A number used to determine in which order to show this topic.'),
        ),
        migrations.AddField(
            model_name='helptopicimage',
            name='order',
            field=models.SmallIntegerField(default=0, help_text='A number used to set the order in which this image is displayed.'),
        ),
    ]
