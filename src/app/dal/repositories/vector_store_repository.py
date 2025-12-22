import chromadb
from typing import Any
from chromadb.api.models.Collection import Collection
from src.app.schemas.vector_db_items_schema import VectorStoreItemsBase

class VectorStoreRepository:

    def __init__(self, config:dict, host: str = "chroma", port: int = 8000):
        self.client = chromadb.HttpClient(host=host, port=port)
        self.config = config

    def get_or_create_collection(self, collection_name: str) -> Collection:
        return self.client.get_or_create_collection(name=collection_name)

    def insert_or_update_items_in_collection(self, collection: Collection, items: VectorStoreItemsBase) -> None:
        collection.upsert(
            ids=items.ids,
            documents=items.documents,
            embeddings=items.embeddings,
            metadatas=items.metadatas,
        )

    def get_collection_items(self, collection: Collection, ids: list[str], columns: list[str]) -> list[dict]:
        
        data = collection.get(ids=ids, include=columns)

        written_items: list[dict] = []

        for chunk_id, doc, meta in zip(data["ids"], data["documents"], data["metadatas"]):
            meta = meta or {}
            written_items.append({
                "id": chunk_id,
                "path": meta.get("path"),
                "chunk": meta.get("chunk"),
                "text_preview": (doc or "")[:200],
            })

        return written_items

    def delete_collection_by_name(self, collection_name:str):

        self.client.delete_collection(name=collection_name)
    
    def delete_items_by_ids(self,collection: Collection,ids:list[str]):

        if not ids:
            return
        
        collection.delete(ids=ids)

    def retrieve_chunks(self, collection: Collection,query_embedding:list[float],top_k: int )->list[dict[str, Any]] :

        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas"],
        )

        if not result.get("ids") or not result["ids"][0]:
            return []

        ids = result["ids"][0]
        docs = result["documents"][0]
        metas = result["metadatas"][0]

        retrieve_chunks: list[dict[str, Any]] = []

        for chunk_id, doc, meta in zip(ids, docs, metas):
            retrieve_chunks.append({
                "id": chunk_id,
                "document": doc  or "",
                "metadata": meta  or {},
            })

        return retrieve_chunks