from assetchat.models import Chat
from filemanager.utils import get_created_or_shared_folder
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class TrainingSerializer(serializers.Serializer):
    chunk_size = serializers.IntegerField(min_value=1)
    overlap_size = serializers.IntegerField(min_value=0)
    clear_existing = serializers.BooleanField()


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField()
    session_id = serializers.CharField()
    temperature = serializers.DecimalField(
        max_digits=2, decimal_places=1, max_value=1.0
    )

    def validate_session_id(self, value):
        try:
            self.context["request"].user.document_chats.get(session_id=value)
        except Chat.DoesNotExist:
            raise ValidationError("Invalid chat.")
        return value


class ChatSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        validated_data = super().validate(attrs)
        folder = validated_data.get("folder")
        if folder is not None:
            folder = get_created_or_shared_folder(
                self.context["request"].user, folder.pk
            )
            if folder is None:
                raise ValidationError(
                    "You don't have permission to chat with this folder."
                )
        return attrs

    def create(self, validated_data):
        chat = Chat(user=self.context["request"].user, **validated_data)
        chat.save()
        return chat

    class Meta:
        model = Chat
        fields = [
            "id",
            "folder",
            "name",
            "session_id",
            "temperature",
            "created_at",
        ]
        read_only_fields = ["id", "session_id", "created_at"]
