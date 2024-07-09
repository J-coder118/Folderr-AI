from functools import cached_property

from django.db import models

PRICE_DECIMAL_MAX_DIGITS = 10
PRICE_DECIMAL_PLACES = 2


class Expense(models.Model):
    file = models.OneToOneField(
        "filemanager.File", related_name="expense", on_delete=models.CASCADE
    )

    summary = models.JSONField(default=dict, editable=False, blank=False)

    line_items = models.JSONField(default=list, editable=False, blank=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        name = getattr(self, "name", None)
        if name is None:
            name = f"Expense for file {self.file.pk}"
        return name

    @cached_property
    def line_item_headers(self):
        headers = []
        for line_item in self.line_items:
            headers += line_item.keys()
        return set(headers)

    class Meta:
        db_table = "expenses"
        ordering = ("-updated_at",)
