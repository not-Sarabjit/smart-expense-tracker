from functools import lru_cache

from langchain_community.embeddings import HuggingFaceEmbeddings


class EmbeddingService:
    """
    Wraps a local HuggingFace embedding model.

    Uses BAAI/bge-small-en-v1.5: free, runs on CPU, 384-dimensional
    vectors, ~90% of OpenAI embedding quality at zero API cost.
    """

    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    def __init__(self) -> None:
        self._model = HuggingFaceEmbeddings(
            model_name=self.MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},  # for cosine distance
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a single piece of text into a 384-dim vector."""
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        return self._model.embed_query(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts at once (more efficient than looping embed_text)."""
        if not texts:
            return []
        return self._model.embed_documents(texts)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """
    Singleton accessor. The model is loaded into memory once (first call
    downloads ~130MB) and reused for every subsequent request.
    """
    return EmbeddingService()


if __name__ == '__main__':
    print('Working Fine')