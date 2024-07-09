# Generated by Django 4.0.8 on 2023-01-23 18:05

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_populate_revenue_cat_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='revenue_cat_app_user_id',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
