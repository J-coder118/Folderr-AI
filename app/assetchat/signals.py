from pathlib import Path

from assetchat.models import AIUsageLimit, Prompt
from assetchat.tasks import store_deleted_vector_task


def remove_current_default_prompt_before_save(
    sender, instance, *args, **kwargs
):
    if instance.default:
        try:
            current_default = Prompt.objects.get(
                prompt_type=instance.prompt_type, default=True
            )
            current_default.default = False
            current_default.save()
        except Prompt.DoesNotExist:
            pass


def mark_related_vector_for_deletion(sender, instance, *args, **kwargs):
    store_deleted_vector_task.delay(
        instance.folder.id, Path(instance.file.name).name
    )


def create_usage_limit_after_signup(
    sender, instance, created, *args, **kwargs
):
    if created:
        AIUsageLimit.objects.create(user=instance)
