# Generated by Django 4.0.10 on 2023-08-20 16:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assetchat", "0005_create_default_prompts"),
    ]

    operations = [
        migrations.CreateModel(
            name="VectorToDelete",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("collection_id", models.UUIDField()),
            ],
        ),
    ]