"""ChromaDB-backed embedding storage and similarity search."""

from __future__ import annotations

from typing import Any, Sequence

import chromadb
from chromadb.api import ClientAPI

from config import CHROMA_DB_PATH


def get_chroma_client() -> ClientAPI:
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_or_create_collection(
    client: ClientAPI,
    name: str = "datapilot_memory",
) -> Any:
    return client.get_or_create_collection(name=name)


def store_embedding(
    client: ClientAPI,
    collection_name: str,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str] | None = None,
    metadatas: list[dict[str, Any]] | None = None,
) -> None:
    col = client.get_or_create_collection(name=collection_name)
    col.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query_similar(
    client: ClientAPI,
    collection_name: str,
    query_embeddings: list[list[float]],
    n_results: int = 5,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]:
    col = client.get_or_create_collection(name=collection_name)
    return col.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where=where,
    )
