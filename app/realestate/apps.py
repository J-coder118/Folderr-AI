from django.apps import AppConfig


class RealestateConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "realestate"

    def ready(self):
        from . import signals

        print(signals)
