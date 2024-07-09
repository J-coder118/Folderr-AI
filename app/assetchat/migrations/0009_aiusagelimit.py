# Generated by Django 4.0.10 on 2023-08-24 09:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assetchat", "0008_chat_temperature"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIUsageLimit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "training_count",
                    models.PositiveSmallIntegerField(default=0),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_usage_limit",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]