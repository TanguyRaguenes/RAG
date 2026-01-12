from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection, QueryResult

from app.schemas.save_items_response_schema import SavedItemBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase


class VectorStoreRepository:
    def __init__(self, config: dict, host: str = "chroma", port: int = 8000):
        self.client = chromadb.HttpClient(host=host, port=port)
        self.config = config

    def get_or_create_collection(self, collection_name: str) -> Collection:
        return self.client.get_or_create_collection(name=collection_name)

    def insert_or_update_items_in_collection(
        self, collection: Collection, items: VectorStoreItemsBase
    ) -> None:
        collection.upsert(
            ids=items.ids,
            documents=items.documents,
            embeddings=items.embeddings,
            metadatas=items.metadatas,
        )

    def get_collection_items(
        self, collection: Collection, ids: list[str], columns: list[str]
    ) -> list[SavedItemBase]:
        data = collection.get(ids=ids, include=columns)

        items: list[SavedItemBase] = []

        for id, document, metadata in zip(
            data["ids"], data["documents"], data["metadatas"]
        ):
            metadata = metadata
            item = SavedItemBase(
                id=id,
                path=metadata.get("path"),
                chunk=document,
                text_preview=document[:200],
            )
            items.append(item)

        return items

    def delete_collection_by_name(self, collection_name: str):
        self.client.delete_collection(name=collection_name)

    def delete_items_by_ids(self, collection: Collection, ids: list[str]):
        if not ids:
            return

        collection.delete(ids=ids)

    def delete_all_items(self, collection: Collection):
        all_data = collection.get()
        if all_data["ids"]:
            collection.delete(ids=all_data["ids"])

    def retrieve_chunks(
        self, collection: Collection, query_embedding: list[float], top_k: int
    ) -> list[dict[str, Any]]:
        response: QueryResult = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas"],
        )

        return response
