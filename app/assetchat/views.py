import json

from assetchat.models import Chat
from assetchat.permissions import CanChat
from assetchat.serializers import (
    ChatSerializer,
    QuestionSerializer,
    TrainingSerializer,
)
from assetchat.tasks import ai_trainer_task, question_answering_task
from assetchat.utils import check_training_required
from django.db import connection
from filemanager.utils import get_created_or_shared_folder
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(http_method_names=["POST"])
@permission_classes([IsAuthenticated])
def start_training(request, folder_pk):
    if request.user.ai_usage_limit.can_train is False:
        raise PermissionDenied(
            detail="You don't have any more training credits left."
        )
    folder = get_created_or_shared_folder(request.user, folder_pk)
    serializer = TrainingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if folder is None:
        return Response(
            {"detail": "You don't have permission to train from this folder."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    chunk_size = serializer.validated_data["chunk_size"]
    overlap_percentage = serializer.validated_data["overlap_size"]
    chunk_overlap = chunk_size * (overlap_percentage / 100)
    result = ai_trainer_task.delay(
        folder_pk=folder_pk,
        chunk_size=chunk_size,
        overlap_size=chunk_overlap,
        clear_existing=serializer.validated_data["clear_existing"],
    )
    return Response({"task_id": result.id})


@api_view(http_method_names=["POST"])
@permission_classes([IsAuthenticated])
def ask_question(request, folder_pk):
    folder = get_created_or_shared_folder(request.user, folder_pk)
    if folder is None:
        return Response(
            {"detail": "You don't have permission to access this folder."},
            status=status.HTTP_403_FORBIDDEN,
        )
    serializer = QuestionSerializer(
        data=request.data, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    task_result = question_answering_task.delay(
        request.user.id,
        serializer.validated_data["question"],
        folder_pk,
        serializer.validated_data["session_id"],
        float(serializer.validated_data["temperature"]),
    )
    return Response({"task_id": task_result.id})


class ChatViewset(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, CanChat]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


@api_view(http_method_names=["GET"])
@permission_classes([IsAuthenticated])
def chat_history(request, chat_pk):
    chat = get_object_or_404(request.user.document_chats.all(), pk=chat_pk)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT message FROM langchain_chat_history WHERE session_id = %s",
            [str(chat.session_id)],
        )
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            message = json.loads(row[0])
            messages.append((message["type"], message["data"]["content"]))
        return Response(messages)


@api_view(http_method_names=["GET"])
@permission_classes([IsAuthenticated])
def training_required(request, folder_pk):
    folder = get_created_or_shared_folder(request.user, folder_pk)
    if folder is None:
        raise NotFound(detail="This folder doesn't exist.")
    if folder.title != "AI":
        raise ValidationError(detail=f"{folder.title} isn't an AI folder.")
    return Response({"training_required": check_training_required(folder)})


@api_view(http_method_names=["GET"])
@permission_classes([IsAuthenticated])
def get_usage_limit(request):
    data = {
        "training_count": request.user.ai_usage_limit.training_count,
        "max_training_count": request.user.ai_usage_limit.max_training_credits,
        "can_train": request.user.ai_usage_limit.can_train,
    }
    return Response(data)
