# Generated by Django 4.0.10 on 2023-05-26 22:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0053_file_quality_score'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sunrun', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_address', models.CharField(max_length=255)),
                ('address_city', models.CharField(max_length=255)),
                ('address_state', models.CharField(max_length=50)),
                ('address_zip', models.CharField(max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('checklist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jobs', to='sunrun.checklist')),
                ('electrical_panel_file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sunrun_job_electrical_panels', to='filemanager.file')),
            ],
            options={
                'db_table': 'sunrun_jobs',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='JobVideo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunrun_job_videos', to='sunrun.job')),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunrun_job_videos', to='filemanager.videofile')),
            ],
            options={
                'db_table': 'sunrun_job_videos',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='JobPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunrun_job_photos', to='filemanager.file')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunrun_job_photos', to='sunrun.job')),
            ],
            options={
                'db_table': 'sunrun_job_photos',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='JobNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunrun_job_notes', to='sunrun.job')),
                ('note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunrun_job_notes', to='filemanager.stickynote')),
            ],
            options={
                'db_table': 'sunrun_job_notes',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddField(
            model_name='job',
            name='notes',
            field=models.ManyToManyField(through='sunrun.JobNote', to='filemanager.stickynote'),
        ),
        migrations.AddField(
            model_name='job',
            name='photos',
            field=models.ManyToManyField(through='sunrun.JobPhoto', to='filemanager.file'),
        ),
        migrations.AddField(
            model_name='job',
            name='receipt_file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sunrun_job_receipts', to='filemanager.file'),
        ),
        migrations.AddField(
            model_name='job',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunrun_jobs', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='job',
            name='videos',
            field=models.ManyToManyField(through='sunrun.JobVideo', to='filemanager.videofile'),
        ),
    ]