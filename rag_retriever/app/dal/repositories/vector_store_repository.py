from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection, QueryResult

from app.schemas.save_items_response_schema import SavedItemBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase

RetrievedChunk = dict[str, Any]


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
    ) -> list[RetrievedChunk]:
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
        enriched_chunks = build_enriched_chunks(documents, metadatas, distances)

        # 4° Filtre les chunks par similarité
        kept_chunks = self.filter_by_similarity(enriched_chunks, minimum_similarity)

        # 5° Sécurité : garantir un nombre minimum de chunks retournés
        if len(kept_chunks) < minimum_number_of_chunks:
            enriched_chunks.sort(key=lambda x: x["similarity"], reverse=True)
            kept_chunks = enriched_chunks[:minimum_number_of_chunks]

        kept_chunks.sort(key=lambda x: x["similarity"], reverse=True)

        return kept_chunks

    def retrieve_document_chunks_by_paths(
        self,
        collection: Collection,
        paths: list[str],
    ) -> list[RetrievedChunk]:
        document_chunks: list[RetrievedChunk] = []
        seen_paths: set[str] = set()

        for path in paths:
            if path in seen_paths:
                continue
            seen_paths.add(path)

            path_chunks = collection.get(
                where={"path": path},
                include=["documents", "metadatas"],
            )

            chunks = build_enriched_chunks(
                path_chunks.get("documents", []) or [],
                path_chunks.get("metadatas", []) or [],
                [0.0 for _ in path_chunks.get("documents", []) or []],
            )
            document_chunks.extend(sort_chunks_by_index(chunks))

        return document_chunks

    def filter_by_similarity(
        self, chunks: list[RetrievedChunk], minimum_similarity: float
    ) -> list[RetrievedChunk]:
        return filter_by_similarity(chunks, minimum_similarity)

    def retrieve_related_chunks(
        self,
        chunks: list[RetrievedChunk],
        collection: Collection,
        max_related_links: int,
    ) -> list[RetrievedChunk]:

        # 1° Extraction des liens et calcul du score
        # Dictionnaire : chemin -> score max hérité
        paths_with_scores = extract_related_links(chunks)

        # 2° Récupération Chroma
        target_paths = sorted(
            paths_with_scores.keys(), key=lambda k: paths_with_scores[k], reverse=True
        )[:max_related_links]

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


def build_enriched_chunks(
    documents: list[str], metadatas: list[dict[str, Any]], distances: list[float]
) -> list[RetrievedChunk]:
    enriched_chunks: list[RetrievedChunk] = []

    for document, metadata, distance in zip(documents, metadatas, distances):
        distance_value = float(distance)
        enriched_chunks.append(
            {
                "document": document,
                "metadata": metadata,
                "distance": distance_value,
                "similarity": 1.0 - distance_value,
            }
        )

    return enriched_chunks


def filter_by_similarity(
    chunks: list[RetrievedChunk], minimum_similarity: float
) -> list[RetrievedChunk]:
    return sorted(
        (chunk for chunk in chunks if chunk["similarity"] >= minimum_similarity),
        key=lambda chunk: chunk["similarity"],
        reverse=True,
    )


def sort_chunks_by_index(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return sorted(
        chunks,
        key=lambda chunk: chunk["metadata"].get("chunk_index", 0),
    )


def extract_related_links(chunks: list[RetrievedChunk]) -> dict[str, float]:
    paths_with_scores: dict[str, float] = {}

    for chunk in chunks:
        metadata = chunk["metadata"]
        parent_score = chunk["similarity"]

        if not metadata["has_links"]:
            continue

        links_str = metadata["related_links"]
        if not links_str:
            continue

        for link in links_str.split(","):
            clean_link = link.strip()
            if not clean_link:
                continue

            # garde le meilleur score si le lien existe déjà
            current = paths_with_scores.get(clean_link)
            paths_with_scores[clean_link] = (
                parent_score if current is None else max(current, parent_score)
            )

    return paths_with_scores
