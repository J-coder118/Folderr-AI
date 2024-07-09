# Generated by Django 4.0.8 on 2022-11-15 20:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_remove_user_is_delete_user_is_verified_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='apple_subject',
            field=models.CharField(blank=True, editable=False, help_text='Apple subject registered claim.', max_length=64),
        ),
    ]