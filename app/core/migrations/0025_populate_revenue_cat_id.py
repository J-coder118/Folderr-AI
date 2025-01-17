# Generated by Django 4.0.8 on 2023-01-23 18:04
import uuid

from django.db import migrations


def up(apps, schema_editor):
    User = apps.get_model('core', 'User')
    for user in User.objects.all():
        user.revenue_cat_app_user_id = uuid.uuid4()
        user.save()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0024_user_revenue_cat_app_user_id'),
    ]

    operations = [
        migrations.RunPython(up, migrations.RunPython.noop)
    ]
