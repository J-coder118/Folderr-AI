from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models


class HelpTopic(models.Model):
    title = models.CharField(max_length=255)
    details = RichTextUploadingField()
    order = models.SmallIntegerField(
        default=0,
        help_text="A number used to determine in which order to show this topic.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "help_topics"
        ordering = ["order"]


class HelpTopicImage(models.Model):
    topic = models.ForeignKey(
        HelpTopic, on_delete=models.CASCADE, related_name="images"
    )
    title = models.CharField(max_length=255)
    file = models.ImageField()
    order = models.SmallIntegerField(
        default=0,
        help_text="A number used to set the order in which this image is displayed.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "help_topic_images"
        ordering = ["order"]
