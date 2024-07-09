import decimal
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from filemanager.models import File

User = get_user_model()


class ProcessedFile(models.Model):
    file = models.OneToOneField(
        File, on_delete=models.CASCADE, related_name="ai_processed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_processed_files"
        ordering = ["-created_at"]


class VectorToDelete(models.Model):
    id = models.UUIDField(primary_key=True, unique=True)
    collection_id = models.UUIDField()

    def __str__(self):
        return str(self.id)


class Prompt(models.Model):
    QUESTION_GENERATOR = 0
    QUESTION_ANSWERING = 1
    PROMPT_TYPE_CHOICES = (
        (QUESTION_GENERATOR, "Question Generator"),
        (QUESTION_ANSWERING, "Question Answering"),
    )
    title = models.CharField(max_length=100, help_text="For internal use.")
    content = models.TextField()
    default = models.BooleanField(default=False)
    prompt_type = models.PositiveSmallIntegerField(
        default=QUESTION_ANSWERING, choices=PROMPT_TYPE_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.default:
            return f"{self.title} (Default)"
        return self.title


class Chat(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_chats",
    )
    folder = models.ForeignKey(
        "filemanager.Folder",
        on_delete=models.CASCADE,
        related_name="document_chats",
    )
    name = models.CharField(max_length=100)
    session_id = models.UUIDField(default=uuid.uuid4)
    temperature = models.DecimalField(
        max_digits=2, decimal_places=1, default=decimal.Decimal("0.5")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat started by {self.user.email} on {self.created_at}"


class AIUsageLimit(models.Model):
    user = models.OneToOneField(
        "core.User", on_delete=models.CASCADE, related_name="ai_usage_limit"
    )
    training_count = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def max_training_credits(self):
        if self.user.membership == User.FREE_MEMBERSHIP:
            return settings.FREE_USER_MAX_TRAINING
        elif self.user.membership == User.PLUS_MEMBERSHIP:
            return settings.PLUS_USER_MAX_TRAINING
        return 0

    @property
    def can_train(self):
        return self.training_count < self.max_training_credits

    def consume_credits(self, count=1):
        self.training_count += count
        self.save()

    def reset_limits(self):
        self.training_count = 0
        self.save()

    def __str__(self):
        return f"Usage limit for {self.user.email}"
