# Generated by Django 4.0.4 on 2022-07-14 10:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0006_alter_suggestedfolder_asset_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suggestedfield',
            name='asset_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suggested_field', to='filemanager.assettype'),
        ),
    ]
