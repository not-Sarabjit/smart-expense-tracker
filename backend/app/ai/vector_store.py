from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore

from app.core.config import settings
from app.ai.embeddings import get_embedding_service

VECTOR_SIZE = 384  # matches BAAI/bge-small-en-v1.5 output dimension


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Singleton Qdrant client, built from settings."""
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,  # None for local/no-auth Qdrant
    )


def init_qdrant_collection() -> None:
    """
    Creates the Qdrant collection if it doesn't already exist.
    Call this once at app startup (main.py lifespan)
    """
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION

    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    """
    Singleton LangChain-compatible vector store, backed by the Qdrant
    collection. This is what ingestion and retrieval code will import.
    """
    return QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=settings.QDRANT_COLLECTION,
        embedding=get_embedding_service()._model,  
    )