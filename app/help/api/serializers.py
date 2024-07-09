from rest_framework import serializers

from backend.aws_setup import download
from help.models import HelpTopic, HelpTopicImage


class HelpTopicImageSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['file'] = download(instance.file.name, allow_download=True)
        return rep

    class Meta:
        model = HelpTopicImage
        exclude = ["topic"]


class HelpTopicSerializer(serializers.ModelSerializer):
    images = HelpTopicImageSerializer(many=True)

    class Meta:
        model = HelpTopic
        fields = "__all__"
