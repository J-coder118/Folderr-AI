from django.apps import AppConfig


class FilemanagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "filemanager"

    def ready(self):
        from . import signals  # noqa: F401
