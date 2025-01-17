# Generated by Django 4.0.4 on 2022-07-06 00:25

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import filemanager.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('content', models.CharField(max_length=500)),
                ('parent', models.ForeignKey(blank=True, null=True,
                                             on_delete=django.db.models.deletion.SET_NULL,
                                             related_name='children',
                                             to='filemanager.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='comments',
                                           to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FolderType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='SuggestedField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=100)),
                ('is_root', models.BooleanField(default=True)),
                ('is_public', models.BooleanField(default=False)),
                ('custom_fields', models.JSONField(
                    default=filemanager.models.folder_default_custom_fields,
                    verbose_name='FolderCustomFields')),
                ('created_by',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                   to=settings.AUTH_USER_MODEL)),
                ('folder_type', models.ForeignKey(default=1,
                                                  on_delete=django.db.models.deletion.CASCADE,
                                                  to='filemanager.foldertype')),
                ('parent', models.ForeignKey(blank=True, null=True,
                                             on_delete=django.db.models.deletion.CASCADE,
                                             related_name='subfolders',
                                             to='filemanager.folder')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id',
                 models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True,
                                  serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('file',
                 models.FileField(upload_to=filemanager.models.File.upload_file_to)),
                ('created_by',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                   to=settings.AUTH_USER_MODEL)),
                ('folder',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                   related_name='files', to='filemanager.folder')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AssetType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('suggested_field',
                 models.ManyToManyField(related_name='asset_type_suggested_fields',
                                        to='filemanager.suggestedfield')),
            ],
        ),
        migrations.CreateModel(
            name='FolderComment',
            fields=[
                ('comment_ptr', models.OneToOneField(auto_created=True,
                                                     on_delete=django.db.models.deletion.CASCADE,
                                                     parent_link=True, primary_key=True,
                                                     serialize=False,
                                                     to='filemanager.comment')),
                ('folder',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                   related_name='comments', to='filemanager.folder')),
            ],
            bases=('filemanager.comment',),
        ),
        migrations.CreateModel(
            name='FileComment',
            fields=[
                ('comment_ptr', models.OneToOneField(auto_created=True,
                                                     on_delete=django.db.models.deletion.CASCADE,
                                                     parent_link=True, primary_key=True,
                                                     serialize=False,
                                                     to='filemanager.comment')),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='comments',
                                           to='filemanager.file')),
            ],
            bases=('filemanager.comment',),
        ),
    ]
