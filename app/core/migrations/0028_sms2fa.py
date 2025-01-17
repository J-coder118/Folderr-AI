# Generated by Django 4.0.10 on 2023-02-23 11:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_totp'),
    ]

    operations = [
        migrations.CreateModel(
            name='SMS2FA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None)),
                ('secret', models.CharField(max_length=255)),
                ('active', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sms_2fas', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
