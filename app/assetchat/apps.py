from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save, pre_save


class AssetchatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assetchat"

    def ready(self):
        from filemanager.models import File

        from . import models, signals

        user_model = get_user_model()

        pre_save.connect(
            signals.remove_current_default_prompt_before_save,
            sender=models.Prompt,
        )

        post_save.connect(
            signals.create_usage_limit_after_signup, sender=user_model
        )

        post_delete.connect(
            signals.mark_related_vector_for_deletion, sender=File
        )
