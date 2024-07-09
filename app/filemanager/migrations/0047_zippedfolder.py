# Generated by Django 4.0.8 on 2023-01-25 11:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0046_defaultnote'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZippedFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zipped_at', models.DateTimeField(auto_now_add=True)),
                ('file', models.FileField(upload_to='')),
                ('downloaded_at', models.DateTimeField(blank=True, null=True)),
                ('folder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zipped', to='filemanager.folder')),
            ],
        ),
    ]