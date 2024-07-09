# Generated by Django 4.0.8 on 2022-11-15 21:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("filemanager", "0016_rename_discription_stickynote_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="Expense",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("summary", models.JSONField(default=dict, editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "file",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="expense",
                        to="filemanager.file",
                    ),
                ),
            ],
            options={
                "db_table": "expenses",
                "ordering": ("-updated_at",),
            },
        ),
        migrations.CreateModel(
            name="LineItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(blank=True, max_length=255)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "qty",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Quantity"
                    ),
                ),
                (
                    "unit_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "expense",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="line_items",
                        to="expenses.expense",
                    ),
                ),
            ],
            options={
                "db_table": "line_items",
                "ordering": ("-updated_at",),
            },
        ),
    ]