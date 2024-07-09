from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in User.objects.all():
            user.receipt_scans = 0
            user.emails_received = 0
            user.save()
