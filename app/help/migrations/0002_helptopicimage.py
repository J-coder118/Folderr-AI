# Generated by Django 4.0.8 on 2022-12-22 00:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('help', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HelpTopicImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('file', models.ImageField(upload_to='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('topic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='help.helptopic')),
            ],
            options={
                'db_table': 'help_topic_images',
            },
        ),
    ]
