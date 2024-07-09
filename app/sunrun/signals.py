import bleach
from sunrun.models import JobNote


def sanitize_note_description(sender, instance: JobNote, *args, **kwargs):
    instance.description = bleach.clean(
        instance.description, tags=bleach.sanitizer.ALLOWED_TAGS + ["p", "br"]
    )
