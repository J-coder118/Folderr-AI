import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from realestate.models import Home

log = logging.getLogger(__name__)


@receiver(post_save, sender=Home)
def save_image_file(sender, instance: Home, created, **kwargs):
    set_image = False
    if not instance.folder.image.name and len(instance.image_url) > 0:
        log.debug("Image is None and image_url exists.")
        set_image = True
    elif instance.folder.image.name and len(instance.image_url) > 0:
        log.debug("Image is not None and image url exists.")
        image_name = instance.folder.image.name
        if image_name is not None:
            log.debug("Image name is not None")
            if len(image_name) == 0:
                log.debug("Image name length is 0")
                set_image = True
        elif image_name is None:
            log.debug("Image name is None")
            set_image = True
    if set_image:
        instance.set_image_from_url()
    else:
        log.debug(
            "Won't set image. Folder image name: %s. Image url: %s",
            instance.folder.image.name,
            instance.image_url,
        )
