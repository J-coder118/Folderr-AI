# Generated by Django 4.0.10 on 2023-08-09 21:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('filemanager', '0062_create_ai_subfolder'),
        ('assetchat', '0001_create_pgvector_extension'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessedFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('file', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ai_processed', to='filemanager.file')),
            ],
            options={
                'db_table': 'ai_processed_files',
                'ordering': ['-created_at'],
            },
        ),
    ]
