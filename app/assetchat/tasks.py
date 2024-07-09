import logging

from assetchat.ai_training import train_from_folder
from assetchat.document_chat import answer_question
from assetchat.file_deletion import get_stale_vector
from assetchat.models import VectorToDelete
from celery import shared_task
from filemanager.models import Folder

log = logging.getLogger("assetchat.tasks")


@shared_task
def ai_trainer_task(folder_pk, chunk_size, overlap_size, clear_existing):
    folder = Folder.objects.get(pk=folder_pk)
    train_from_folder(folder, chunk_size, overlap_size, clear_existing)
    return {"contents": {"success": True}}


@shared_task
def question_answering_task(
    user_id: int,
    question: str,
    folder_pk: int,
    session_id: str,
    temperature: float,
):
    folder = Folder.objects.get(pk=folder_pk)
    result = answer_question(question, folder, session_id, temperature)
    return {"user_id": user_id, "contents": {"answer": result["answer"]}}


@shared_task
def store_deleted_vector_task(folder_id, file_name):
    folder = Folder.objects.get(pk=folder_id)
    if folder.title == "AI":
        log.debug("Folder %d is AI.", folder_id)
        vector_info = get_stale_vector(folder, file_name)
        if vector_info is not None:
            log.debug("Received vector_info: %s", vector_info)
            VectorToDelete.objects.get_or_create(
                id=vector_info["vector_id"],
                collection_id=vector_info["collection_id"],
            )
        else:
            log.debug("Vector info was None.")
    else:
        log.debug("Folder %d isn't AI.", folder_id)
