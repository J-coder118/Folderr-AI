# Generated by Django 4.0.4 on 2022-07-19 05:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0008_folder_asset_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='folder',
            name='asset_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='filemanager.assettype'),
        ),
    ]
