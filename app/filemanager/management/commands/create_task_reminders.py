from django.core.management import BaseCommand

from filemanager.models import Task


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        for task in Task.objects.all():
            if task.should_remind():
                task.create_reminder()
                self.stdout.write(f"Reminder created for task {task.id}.")
