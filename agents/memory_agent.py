"""Memory / retrieval agent wired to vector store (stub)."""

from memory import vector_store


class MemoryAgent:
    def __init__(self, collection_name: str = "datapilot_memory"):
        self._collection_name = collection_name
        self._client = vector_store.get_chroma_client()

    def process(self, *args, **kwargs):
        """Placeholder for RAG-style memory operations."""
        raise NotImplementedError
