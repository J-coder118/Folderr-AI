import logging
import secrets
from io import BytesIO

import requests
from django.core.files.images import ImageFile
from django.db import IntegrityError, models
from filemanager.models import Folder
from PIL import Image
from realestate.zillow import ZillowClient

log = logging.getLogger(__name__)


class Home(models.Model):
    folder = models.OneToOneField(
        "filemanager.Folder", on_delete=models.CASCADE, related_name="home"
    )
    full_address = models.CharField(max_length=500)
    home_type = models.CharField(max_length=64, default="Unknown")
    price_estimate = models.CharField(max_length=20, default="Unknown")
    last_sold_price = models.CharField(max_length=20, default="Unknown")
    year_built = models.PositiveSmallIntegerField(null=True, blank=True)
    lot_size = models.CharField(max_length=8, blank=True)
    living_area = models.PositiveSmallIntegerField(null=True, blank=True)
    no_of_bathrooms = models.PositiveSmallIntegerField(
        "Number of Bathrooms", null=True, blank=True
    )
    no_of_full_bathrooms = models.PositiveSmallIntegerField(
        "Number of Full Bathrooms", null=True, blank=True
    )
    no_of_half_bathrooms = models.PositiveSmallIntegerField(
        "Number of Half Bathrooms", null=True, blank=True
    )
    no_of_quarter_bathrooms = models.PositiveSmallIntegerField(
        "Number of Quarter Bathrooms", null=True, blank=True
    )
    no_of_bedrooms = models.PositiveSmallIntegerField(
        "Number of Bedrooms", null=True, blank=True
    )
    image_url = models.URLField(blank=True)

    def set_image_from_url(self):
        if len(self.image_url) > 0:
            log.debug("Setting image")
            response = requests.get(self.image_url)
            image_io = BytesIO(response.content)
            with Image.open(image_io) as image:
                fmt = image.format
                django_image_file = ImageFile(
                    file=image_io,
                    name=f"{secrets.token_urlsafe(4)}.{fmt.lower()}",
                )
                self.folder.image = django_image_file
                self.folder.save()

    @classmethod
    def get_or_create_from_address(
        cls, folder_id, full_address, force: bool = False
    ) -> tuple[bool, (models.Model | str)]:
        """
        Create an instance from an address string.

        Fetch data from Zillow api to populate model
        attributes.
        """
        create = False

        try:
            instance = cls.objects.get(full_address=full_address)
        except cls.DoesNotExist:
            folder = Folder.objects.get(pk=folder_id)
            if hasattr(folder, "home"):
                instance = folder.home
            else:
                instance = cls(folder=folder, full_address=full_address)
            create = True
        if create or force:
            if "undefined" not in full_address:
                zillow = ZillowClient(full_address)
                success, home_details = zillow.get_home_details()
                if success:
                    for field, field_value in home_details.items():
                        if field_value is not None:
                            setattr(instance, field, field_value)
        try:
            instance.save()
        except IntegrityError as e:
            log.exception(e)
        except Exception as e:
            log.exception(e)
        return create, instance

    def __str__(self):
        return f"Home at {self.full_address}"
