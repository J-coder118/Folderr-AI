# Generated by Django 4.0.8 on 2022-12-30 11:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('realestate', '0003_remove_home_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='home',
            name='full_address',
            field=models.CharField(max_length=500),
        ),
    ]
