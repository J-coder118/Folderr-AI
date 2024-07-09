from django.core.management import BaseCommand

from filemanager.models import Task


class Command(BaseCommand):
    def handle(self, *args, **options):
        for task in Task.objects.all():
            task.repeat_task()
