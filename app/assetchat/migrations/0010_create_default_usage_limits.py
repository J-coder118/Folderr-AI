# Generated by Django 4.0.10 on 2023-08-24 09:32
from django.db import migrations


def up(apps, schema_editor):
    user_model = apps.get_model("core", "User")
    usage_limit_model = apps.get_model("assetchat", "AIUsageLimit")
    to_create = []
    for user in user_model.objects.all():
        to_create.append(usage_limit_model(user=user))
    usage_limit_model.objects.bulk_create(to_create)


def down(apps, schema_editor):
    usage_limit_model = apps.get_model("assetchat", "AIUsageLimit")
    usage_limit_model.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("assetchat", "0009_aiusagelimit"),
    ]

    operations = [migrations.RunPython(up, down)]
