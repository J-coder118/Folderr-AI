import logging
import uuid

from backend.aws_setup import download
from core.serializers import UserSerializer
from realestate.models import Home
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import (
    AssetType,
    Comment,
    File,
    Folder,
    FolderTransfer,
    IgnoredSuggestedFolder,
    Share,
    SharedFile,
    ShareNotification,
    StickyNote,
    SuggestedField,
    SuggestedFolder,
    Task,
    TaskReminder,
    VideoFile,
    ZippedFolder,
)

log = logging.getLogger(__name__)


class ShareSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(
        default=serializers.CurrentUserDefault(), read_only=True
    )

    class Meta:
        model = Share
        fields = "__all__"

    def to_representation(self, instance):
        res = super().to_representation(instance)
        if instance.folder:
            res["folder"] = Folder.objects.filter(
                id=instance.folder.id
            ).values()
        if instance.receiver:
            res["receiver"] = {
                "id": instance.receiver.id,
                "first_name": instance.receiver.first_name,
                "last_name": instance.receiver.last_name,
                "email": instance.receiver.email,
            }
        res["sender"] = {
            "id": instance.sender.id,
            "first_name": instance.sender.first_name,
            "last_name": instance.sender.last_name,
            "email": instance.sender.email,
        }
        return res

    def validate(self, attrs):
        folder = attrs.get("folder")
        if not Folder.objects.filter(id=folder.id).exists():
            raise serializers.ValidationError("selected Folder is not exists")
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(
        default=serializers.CurrentUserDefault(), read_only=True
    )

    class Meta:
        model = Comment
        fields = "__all__"


class FileSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(default=uuid.uuid4)
    created_by = serializers.StringRelatedField(
        default=serializers.CurrentUserDefault(), read_only=True
    )

    class Meta:
        model = File
        exclude = ["_mime_type"]

    def validate(self, attrs):
        file = attrs.get("file")
        if file is not None:
            user = self.context["request"].user
            if not user.can_upload(file.size):
                raise ValidationError("Disk usage limit reached.")
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance):
        rep = super(FileSerializer, self).to_representation(instance)
        rep["folder"] = {
            "id": instance.folder.id,
            "title": instance.folder.title,
        }
        rep["file"] = download(instance.file.name, True)
        if instance.thumbnail.name:
            rep["thumbnail"] = download(instance.thumbnail.name, True)
        rep["isImage"] = instance.is_image
        rep["mime_type"] = instance.mime_type
        return rep


class FolderCreateSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if validated_data["title"] == "AI":
            raise ValidationError("Only a single AI folder is allowed.")

    class Meta:
        model = Folder
        fields = ["title", "isPublic", "user", "parent"]


class FolderBaseSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    files = FileSerializer(many=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            "id",
            "user",
            "title",
            "created",
            "updated",
            "files",
            "isPublic",
            "parent",
            "children",
        ]

    def get_children(self, obj):
        return [FolderBaseSerializer(x).data for x in obj.children.all()]


class StickyNoteSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(
        default=serializers.CurrentUserDefault(), read_only=True
    )

    class Meta:
        model = StickyNote
        fields = "__all__"

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res["folder"] = {
            "id": instance.folder.id,
            "title": instance.folder.title,
        }
        return res


class SubFolderSerailizer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)
    stickynotes = StickyNoteSerializer(many=True, read_only=True)
    shared_with = ShareSerializer(many=True, read_only=True)

    class Meta:
        model = Folder
        fields = (
            "id",
            "created",
            "updated",
            "title",
            "is_root",
            "is_public",
            "custom_fields",
            "created_by",
            "parent",
            "folder_type",
            "asset_type",
            "files",
            "stickynotes",
            "shared_with",
            "email",
        )


class VideoFileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = download(instance.file.name, allow_download=True)
        if instance.thumbnail.name:
            rep["thumbnail"] = download(
                instance.thumbnail, allow_download=True
            )
        return rep

    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None:
            user = self.context["request"].user
            folder = attrs.get("folder")
            if folder is not None:
                if folder.created_by != user:
                    log.info(
                        "User %d is trying to save a video to folder %d which doesn't belong to him.",
                        user.pk,
                        folder.pk,
                    )
                    raise ValidationError(
                        "The selected folder doesn't belong to you."
                    )
        return attrs

    class Meta:
        model = VideoFile
        fields = "__all__"
        read_only_fields = ["status", "created_at", "updated_at"]


class FolderSerializer(serializers.ModelSerializer):
    subfolders = SubFolderSerailizer(many=True, read_only=True)
    stickynotes = StickyNoteSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(
        default=serializers.CurrentUserDefault(), read_only=True
    )
    shared_with = ShareSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.image.name:
            rep["image"] = download(instance.image.name, allow_download=True)
        elif instance.asset_type.title == "HOME":
            try:
                home = Home.objects.get(full_address=instance.full_address)
                if img := home.folder.image.name:
                    rep["image"] = download(img, allow_download=True)
            except Home.DoesNotExist:
                pass
        return rep

    class Meta:
        model = Folder
        fields = (
            "id",
            "created",
            "updated",
            "title",
            "is_root",
            "is_public",
            "custom_fields",
            "created_by",
            "parent",
            "folder_type",
            "asset_type",
            "subfolders",
            "stickynotes",
            "shared_with",
            "email",
            "image",
        )
        read_only_fields = ["email"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        super().update(instance, validated_data)
        new_fields = validated_data.get("custom_fields")
        instance.title = validated_data.get("title", instance.title)
        instance.parent = validated_data.get("parent", instance.parent)
        if new_fields is not None:
            new_data = {**instance.custom_fields, **new_fields}
            instance.custom_fields = new_data
        instance.save()
        return instance


class SuggestedFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedFolder
        fields = "__all__"


class SuggestedFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedField
        fields = "__all__"


class AssetTypeSerializer(serializers.ModelSerializer):
    suggested_folder = SuggestedFolderSerializer(many=True, read_only=True)
    suggested_field = SuggestedFieldSerializer(many=True, read_only=True)

    class Meta:
        model = AssetType
        fields = (
            "id",
            "title",
            "suggested_folder",
            "suggested_field",
            "hidden",
        )


class OnlyAssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = ("id", "title")


class FileSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ["id", "created", "created_by", "file_name", "folder"]

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res["folder"] = {
            "id": instance.folder.id,
            "title": instance.folder.title,
            "is_root": instance.folder.is_root,
        }
        if instance.folder.parent:
            res["folder"] = {
                **res["folder"],
                "parent": instance.folder.parent.id,
                "parent_name": instance.folder.parent.title,
            }
        return res


class SendShareFolderMailSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(
        default=serializers.CurrentUserDefault(), read_only=True
    )
    email = serializers.EmailField(max_length=256)

    class Meta:
        model = Share
        fields = ["folder", "sender", "permission", "email"]


class FolderSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "created", "created_by", "title", "is_root", "parent"]

    def to_representation(self, instance):
        res = super().to_representation(instance)
        if instance.parent:
            res["parent_name"] = instance.parent.title
        return res


# class UserActivitySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = UserActivity
#         fields = "__all__"
#
#     def to_representation(self, instance):
#         res = super().to_representation(instance)
#         if instance.file:
#             res["file"] = {
#                 "id": instance.file.id,
#                 "file_name": instance.file.file_name,
#             }
#         if instance.folder:
#             res["folder"] = {
#                 "id": instance.folder.id,
#                 "title": instance.folder.title,
#                 "is_root": instance.folder.is_root,
#             }
#             if instance.folder.parent:
#                 res["folder"] = {
#                     **res["folder"],
#                     "parent": instance.folder.parent.id,
#                     "parent_name": instance.folder.parent.title,
#                 }
#         if instance.comment:
#             res["comment"] = {
#                 "id": instance.comment.id,
#                 "comment": instance.comment.comment,
#             }
#             if instance.comment.folder:
#                 res["comment"] = {
#                     **res["comment"],
#                     "folder": {
#                         "id": instance.comment.folder.id,
#                         "title": instance.comment.folder.title,
#                         "is_root": instance.comment.folder.is_root,
#                     },
#                 }
#                 if instance.comment.folder.parent:
#                     res["comment"] = {
#                         **res["comment"],
#                         "parent": instance.comment.folder.parent.id,
#                     }
#             if instance.comment.file:
#                 res["comment"] = {
#                     **res["comment"],
#                     "file": {
#                         "id": instance.comment.file.id,
#                         "file_name": instance.comment.file.file_name,
#                     },
#                 }
#         res["user"] = {
#             "first_name": instance.user.first_name,
#             "last_name": instance.user.last_name,
#         }
#         return res


class TaskSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(
        default=serializers.CurrentUserDefault(), read_only=True
    )
    start_at = serializers.DateTimeField(required=False)
    recurrences = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    class Meta:
        model = Task
        fields = "__all__"


class TaskReminderSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["task"] = {
            "id": instance.task.id,
            "title": instance.task.title,
            "due_at": instance.task.due_at,
        }
        return rep

    class Meta:
        model = TaskReminder
        fields = "__all__"


class IgnoredSuggestedFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = IgnoredSuggestedFolder
        exclude = ["user"]


class ShareNotificationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super(ShareNotificationSerializer, self).to_representation(
            instance
        )
        rep["folder"] = instance.share.folder_id
        return rep

    class Meta:
        model = ShareNotification
        fields = ["id", "content"]


class ZippedFolderSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["file"] = download(instance.file.name, allow_download=True)
        return rep

    class Meta:
        model = ZippedFolder
        fields = ["file"]


class SharedFileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.content_type.model == "file":
            file_name = instance.content_object.file_name
            if instance.content_object.is_image:
                mime_type = "image"
            else:
                mime_type = "pdf"
        else:
            file_name = instance.content_object.title
            mime_type = "video"

        rep.update(
            {
                "file_name": file_name,
                "file_type": instance.content_type.model,
                "file": download(instance.content_object.file.name),
                "thumbnail": download(instance.content_object.thumbnail.name),
                "mime_type": mime_type,
            }
        )
        return rep

    class Meta:
        model = SharedFile
        fields = ["id", "created_at", "updated_at"]


class PerformFolderTransferSerializer(serializers.Serializer):
    to_email = serializers.EmailField()


class TransferredFolderSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["folder_title"] = instance.folder.title
        return rep

    class Meta:
        model = FolderTransfer
        fields = ["id", "to_email", "created_at", "updated_at"]
