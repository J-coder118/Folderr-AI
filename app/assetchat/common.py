from django.conf import settings
from django.utils.text import slugify
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import PGVector


def get_vector_store(collection_name: str):
    embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_SECRET_KEY)
    return PGVector.from_existing_index(
        embeddings,
        collection_name=collection_name,
        connection_string=POSTGRES_CONNECTION_STRING,
    )


def get_collection_name(folder):
    return f"{folder.parent.title}_{slugify(folder.created_by.email)}"


POSTGRES_CONNECTION_STRING = f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB_NAME}"


def get_collection_id(collection_name, cursor):
    cursor.execute(
        """SELECT uuid FROM langchain_pg_collection WHERE name = %s""",
        [collection_name],
    )
    row = cursor.fetchone()
    if row is not None:
        if len(row) > 0:
            return row[0]
