# Generated by Django 4.0.8 on 2022-11-16 18:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='line_items',
            field=models.JSONField(default=list, editable=False),
        ),
        migrations.DeleteModel(
            name='LineItem',
        ),
    ]
