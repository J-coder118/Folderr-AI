from django.apps import AppConfig
from django.db.models.signals import pre_save


class SunrunConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sunrun"

    def ready(self):
        from . import models, signals

        pre_save.connect(
            signals.sanitize_note_description, sender=models.JobNote
        )
