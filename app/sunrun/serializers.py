from backend.aws_setup import download
from rest_framework import serializers
from sunrun.models import Checklist, Job, JobNote, JobPhoto, JobVideo


class ChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checklist
        exclude = ["user"]


class JobPhotoSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = {
            "url": download(instance.file.name),
            "name": instance.file.name,
        }
        return rep

    class Meta:
        model = JobPhoto
        fields = "__all__"


class JobVideoSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = {
            "url": download(instance.video.name),
            "name": instance.video.name,
        }
        return rep

    class Meta:
        model = JobVideo
        fields = "__all__"


class JobNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobNote
        fields = "__all__"


class JobSerializer(serializers.ModelSerializer):
    notes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    photos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    videos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if receipt_file := getattr(instance.receipt_file, "name"):
            rep["receipt_file"] = download(receipt_file.name)
        if electrical_panel_file := getattr(
            instance.electrical_panel_file, "name"
        ):
            rep["electrical_panel_file"] = download(electrical_panel_file.name)
        return rep

    class Meta:
        model = Job
        exclude = ["user"]
