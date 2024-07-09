from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        site = Site.objects.get(pk=settings.SITE_ID)
        site.domain = settings.DOMAIN_NAME
        site.save()
