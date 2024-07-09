import logging

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

User = get_user_model()

log = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in User.objects.all():
            user.sync_membership()
