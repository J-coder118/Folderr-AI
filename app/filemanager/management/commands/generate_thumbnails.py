from django.core.management import BaseCommand

from filemanager.models import File


class Command(BaseCommand):
    def handle(self, *args, **options):
        for file in File.objects.all():
            file.make_thumbnail()
