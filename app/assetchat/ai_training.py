import logging
import tempfile
from pathlib import Path
from typing import TypedDict

import magic
from assetchat.common import (
    get_collection_id,
    get_collection_name,
    get_vector_store,
)
from assetchat.models import ProcessedFile, VectorToDelete
from django.core.files import File
from django.db import connection
from filemanager.models import Folder
from langchain.document_loaders import PyMuPDFLoader
from langchain.document_loaders import TextLoader as LangChainTextLoader
from langchain.document_loaders import (
    UnstructuredFileLoader,
    UnstructuredImageLoader,
    UnstructuredWordDocumentLoader,
)
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

log = logging.getLogger("assetchat.utils")

PathList = list[Path]
DocumentList = list[Document]

ImageLoader = UnstructuredImageLoader
MicrosoftWordLoader = UnstructuredWordDocumentLoader
PDFLoader = PyMuPDFLoader
TextLoader = LangChainTextLoader
UnknownFileLoader = UnstructuredFileLoader


class MimePathMap(TypedDict):
    plaintext: PathList
    microsoft_word: PathList
    pdf: PathList
    image: PathList
    unknown: PathList


class MimeDocumentMap(TypedDict):
    plaintext: DocumentList
    microsoft_word: DocumentList
    pdf: DocumentList
    image: DocumentList
    unknown: DocumentList


mime_loader_map = {
    "plaintext": TextLoader,
    "microsoft_word": MicrosoftWordLoader,
    "pdf": PDFLoader,
    "image": ImageLoader,
    "unknown": UnknownFileLoader,
}


def get_file_name(file: File):
    path = Path(file.name)
    return path.name


def write_file_to_tmp_dir(file: File, tmp_dir: Path):
    file_path = tmp_dir / get_file_name(file)
    with file_path.open("wb") as target_fp:
        for chunk in file.chunks():
            target_fp.write(chunk)
    log.info("File written to %s.", file_path)
    return file_path


def get_mime_map(paths: PathList) -> MimePathMap:
    mime_map: MimePathMap = {
        "plaintext": [],
        "microsoft_word": [],
        "pdf": [],
        "image": [],
        "unknown": [],
    }
    for path in paths:
        mime_type = magic.from_file(str(path), mime=True)
        if mime_type in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            mime_map["microsoft_word"].append(path)
        elif mime_type == "application/pdf":
            mime_map["pdf"].append(path)
        elif mime_type == "text/plain":
            mime_map["plaintext"].append(path)
        elif mime_type.find("image") != -1:
            mime_map["image"].append(path)
        else:
            mime_map["unknown"].append(path)
    log.debug("Mime map:\n\n %s", mime_map)
    return mime_map


def load_documents(mime_map: MimePathMap) -> MimeDocumentMap:
    document_map: MimeDocumentMap = {
        "plaintext": [],
        "microsoft_word": [],
        "pdf": [],
        "image": [],
        "unknown": [],
    }

    for file_type, file_paths in mime_map.items():
        log.info("Loading %s files.", file_type)
        loader_class = mime_loader_map[file_type]
        for file_path in file_paths:
            log.info("Loading file at path %s.", file_path)
            loader = loader_class(str(file_path))
            document_map[file_type] += loader.load()  # type: ignore
    log.debug("Document map:\n\n %s", document_map)
    return document_map


def split_documents(
    document_map: MimeDocumentMap, chunk_size, overlap_size
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=overlap_size
    )
    documents_to_split = []
    for documents in document_map.values():
        documents_to_split += documents

    return splitter.split_documents(documents_to_split)


def delete_stale_vectors(collection_name):
    with connection.cursor() as cursor:
        collection_id = get_collection_id(collection_name, cursor)
        if collection_id is not None:
            log.debug("Got collection_id %s", collection_id)
            vectors_to_delete = VectorToDelete.objects.filter(
                collection_id=collection_id
            )
            log.info(
                "%d vectors queued for deletion.", vectors_to_delete.count()
            )
            for vector in vectors_to_delete:
                log.debug("Will delete vector %s", vector.id)
                cursor.execute(
                    """DELETE FROM langchain_pg_embedding WHERE collection_id = %s
                    AND uuid = %s""",
                    [str(collection_id), str(vector.id)],
                )
                log.debug("Deleted vector %s", vector.id)
            vectors_to_delete.delete()
        else:
            log.debug("Collection id was None.")


def train_from_folder(
    folder: Folder, chunk_size, overlap_size, clear_existing: False
):
    collection_name = get_collection_name(folder)
    vector_store = get_vector_store(collection_name)
    if clear_existing:
        vector_store.delete_collection()
        vector_store.create_collection()
        for folderr_file in folder.files.all():
            if hasattr(folderr_file, "ai_processed"):
                folderr_file.ai_processed.delete()
    else:
        delete_stale_vectors(collection_name)
    unprocessed_files = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        saved_paths = []
        for folderr_file in folder.files.all():
            if not hasattr(folderr_file, "ai_processed"):
                log.info("File %s will be ingested.", folderr_file.pk)
                unprocessed_files.append(folderr_file)
                file_path = write_file_to_tmp_dir(
                    folderr_file.file, Path(tmp_dir)
                )
                saved_paths.append(file_path)
        mime_map = get_mime_map(saved_paths)
        document_map = load_documents(mime_map)
        documents = split_documents(document_map, chunk_size, overlap_size)
        vector_store.add_documents(documents)
    ProcessedFile.objects.bulk_create(
        [
            ProcessedFile(file=unprocessed_file)
            for unprocessed_file in unprocessed_files
        ]
    )
    credit_count = 1
    if clear_existing:
        credit_count += 1
    folder.created_by.ai_usage_limit.consume_credits(credit_count)
