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
        collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        return collection

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
            item = SavedItemBase(
                id=id,
                chunk=document,
                metadatas=metadata,
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

    # Récupère les top_k chunks depuis Chroma, calcule la similarité cosinus,
    # filtre selon un seuil minimum et garantit un nombre minimum de résultats.

    def retrieve_chunks_filtered(
        self,
        collection: Collection,
        query_embedding: list[float],
        top_k: int,
        minimum_similarity: float,
        minimum_number_of_chunks: int,
    ) -> list[dict[str, Any]]:
        # 1° Récupération des chunks bruts depuis Chroma
        retrieved_chunks: QueryResult = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # 2° Extraction des résultats (une seule requête → index 0)
        documents = retrieved_chunks.get("documents", [[]])[0] or []
        metadatas = retrieved_chunks.get("metadatas", [[]])[0] or []
        distances = retrieved_chunks.get("distances", [[]])[0] or []

        # 3° Enrichissement des chunks avec distance et similarité
        enriched_chunks = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            # En cosinus (cosine en anglais) : similarité ≈ 1 - distance

            enriched_chunks.append(
                {
                    "document": document,
                    "metadata": metadata,
                    "distance": float(distance),
                    "similarity": 1.0 - float(distance),
                }
            )

        # 4° Filtre les chunks par similarité
        kept_chunks = self.filter_by_similarity(enriched_chunks, minimum_similarity)

        # 5° Sécurité : garantir un nombre minimum de chunks retournés
        if len(kept_chunks) < minimum_number_of_chunks:
            enriched_chunks.sort(key=lambda x: x["similarity"], reverse=True)
            kept_chunks = enriched_chunks[:minimum_number_of_chunks]

        # 6° On va chercher les chunks liés
        enriched_kept_chunks = self.retrieve_related_chunks(kept_chunks, collection)
        enriched_kept_chunks.sort(key=lambda x: x["similarity"], reverse=True)

        return enriched_kept_chunks

    def filter_by_similarity(
        self, chunks: list, minimum_similarity: float
    ) -> list[dict[str, Any]]:
        # 1° Tri par similarité décroissante (meilleurs chunks en premier)
        chunks.sort(key=lambda chunk: chunk["similarity"], reverse=True)

        # 4° Filtrage : on conserve uniquement les chunks suffisamment pertinents
        kept_chunks: list[dict[str, Any]] = [
            chunk for chunk in chunks if chunk["similarity"] >= minimum_similarity
        ]

        return kept_chunks

    def retrieve_related_chunks(
        self, chunks: list, collection: Collection
    ) -> list[dict[str, Any]]:
        # Dictionnaire : chemin -> score max hérité
        paths_with_scores = {}

        # 1° Extraction des liens et calcul du score
        for chunk in chunks:
            metadata = chunk["metadata"]
            parent_score = chunk["similarity"]

            if metadata["has_links"]:
                links_str = metadata["related_links"]
                if links_str:
                    links = links_str.split(",")
                    for link in links:
                        clean_link = link.strip()
                        if clean_link:
                            # Si le lien existe déjà, on garde le meilleur score des parents
                            if clean_link in paths_with_scores:
                                paths_with_scores[clean_link] = max(
                                    paths_with_scores[clean_link], parent_score
                                )
                            else:
                                paths_with_scores[clean_link] = parent_score

        # 2° Récupération Chroma
        target_paths = list(paths_with_scores.keys())

        if target_paths:
            related_chunks = collection.get(
                where={"path": {"$in": target_paths}},
                include=["documents", "metadatas"],
            )

            # 3° Ajout aux résultats
            if related_chunks and related_chunks["documents"]:
                for document, metadata in zip(
                    related_chunks["documents"], related_chunks["metadatas"]
                ):
                    inherited_score = paths_with_scores[metadata["path"]]

                    related_chunk = {
                        "document": f"CONTEXTE : DOCUMENT LIÉ (Détail)\n{document}",
                        "metadata": metadata,
                        "distance": 0.0,
                        "similarity": inherited_score,
                    }

                    # 4° Anti-doublon
                    is_duplicate = any(
                        chunk["document"] == related_chunk["document"]
                        for chunk in chunks
                    )

                    if not is_duplicate:
                        chunks.append(related_chunk)

        return chunks
