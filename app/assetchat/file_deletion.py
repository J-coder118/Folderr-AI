import logging
from pathlib import Path
from uuid import UUID

from assetchat.common import get_collection_id, get_collection_name
from assetchat.models import VectorToDelete
from django.db import connection
from filemanager.models import Folder

log = logging.getLogger("assetchat.file_deletion")


def get_stale_vector(folder: Folder, target_file_name: str) -> dict | None:
    collection_name = get_collection_name(folder)
    with connection.cursor() as cursor:
        collection_id = get_collection_id(collection_name, cursor)
        if collection_id is not None:
            log.debug("Got collection id %s", collection_id)
            cursor.execute(
                """SELECT uuid, cmetadata -> 'source' AS "source_doc" FROM
            langchain_pg_embedding WHERE collection_id = %s""",
                [str(collection_id)],
            )
            rows = cursor.fetchall()
            log.debug("Selected %d rows", len(rows))
            for row in rows:
                log.debug("Working with row %s", row)
                vector_id, source_document = row
                log.debug(
                    "Vector id: %s\nsource doc: %s", vector_id, source_document
                )
                file_name = Path(source_document).name
                log.debug("File name: %s", file_name)
                if file_name == target_file_name:
                    return {
                        "vector_id": vector_id,
                        "collection_id": collection_id,
                    }
                else:
                    log.debug(
                        "%s is not equal to %s", file_name, target_file_name
                    )
        else:
            log.debug("Collection id was None.")


def enumerate_stale_vectors():
    stale_vectors = []
    root_folders = Folder.objects.filter(is_root=True)
    for root_folder in root_folders:
        ai_folder = root_folder.subfolders.get(title="AI")
        collection_name = get_collection_name(ai_folder)
        current_file_names = [
            folderr_file.file.name for folderr_file in ai_folder.files.all()
        ]
        with connection.cursor() as cursor:
            collection_id = get_collection_id(collection_name, cursor)
            if collection_id is not None:
                cursor.execute(
                    """SELECT uuid, cmetadata -> 'source' AS "source_doc" FROM
                    langchain_pg_embedding WHERE collection_id = %s""",
                    [str(collection_id)],
                )
                rows = cursor.fetchall()
                file_name_to_vector_id_map = {}
                for row in rows:
                    vector_id, source_document = row
                    file_name_to_vector_id_map[
                        str(Path(source_document).name)
                    ] = vector_id
                for file_name, vector_id in file_name_to_vector_id_map.items():
                    if file_name not in current_file_names:
                        stale_vectors.append(
                            {
                                "collection_id": collection_id,
                                "vector_id": vector_id,
                            }
                        )
    for stale_vector in stale_vectors:
        VectorToDelete.objects.get_or_create(
            id=UUID(stale_vector["vector_id"]),
            collection_id=stale_vector["collection_id"],
        )
