from typing import Any
import time

import chromadb
from chromadb.api.models.Collection import Collection, QueryResult

from app.core.exceptions import VectorStoreException
from app.core.metrics import retriever_chroma_duration_seconds
from app.schemas.save_items_response_schema import SavedItemBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase

RetrievedChunk = dict[str, Any]


class VectorStoreRepository:
    def __init__(self, config: dict, host: str = "chroma", port: int = 8000):
        """Initialise le client HTTP ChromaDB.

        Args:
            config: Configuration applicative du retriever.
            host: Nom DNS ou hôte ChromaDB.
            port: Port HTTP ChromaDB.

        Returns:
            Aucune valeur.

        Raises:
            ValueError: Si ChromaDB refuse les paramètres de connexion.
        """
        self.client = chromadb.HttpClient(host=host, port=port)
        self.config = config

    def get_or_create_collection(self, collection_name: str) -> Collection:
        """Récupère ou crée une collection ChromaDB en distance cosinus.

        Args:
            collection_name: Nom de la collection à récupérer ou créer.

        Returns:
            Collection ChromaDB prête à être utilisée.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant la création ou récupération.
        """
        start = time.perf_counter()
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                configuration={"hnsw": {"space": "cosine"}},
            )
        except Exception as exception:
            _record_chroma_error("get_or_create_collection", start)
            raise VectorStoreException(
                message="Impossible de récupérer ou créer la collection ChromaDB",
                details={"collection": collection_name},
            ) from exception
        _record_chroma_success("get_or_create_collection", start)
        return collection

    def insert_or_update_items_in_collection(
        self, collection: Collection, items: VectorStoreItemsBase
    ) -> None:
        """Insère ou met à jour des items vectoriels dans une collection.

        Args:
            collection: Collection ChromaDB cible.
            items: Items vectoriels à persister.

        Returns:
            Aucune valeur.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant l'upsert.
        """
        start = time.perf_counter()
        try:
            collection.upsert(
                ids=items.ids,
                documents=items.documents,
                embeddings=items.embeddings,
                metadatas=items.metadatas,
            )
        except Exception as exception:
            _record_chroma_error("upsert", start)
            raise VectorStoreException(
                message="Impossible d'insérer ou mettre à jour les items ChromaDB",
                details={"item_count": len(items.ids)},
            ) from exception
        _record_chroma_success("upsert", start)

    def get_collection_items(
        self, collection: Collection, ids: list[str], columns: list[str]
    ) -> list[SavedItemBase]:
        """Relit des items d'une collection ChromaDB.

        Args:
            collection: Collection ChromaDB source.
            ids: Identifiants des items à relire.
            columns: Colonnes ChromaDB à inclure dans la réponse.

        Returns:
            Items sauvegardés au format de réponse API.

        Raises:
            VectorStoreException: Si ChromaDB échoue ou retourne des listes incohérentes.
        """
        start = time.perf_counter()
        try:
            data = collection.get(ids=ids, include=columns)
        except Exception as exception:
            _record_chroma_error("get_collection_items", start)
            raise VectorStoreException(
                message="Impossible de relire les items ChromaDB",
                details={"item_count": len(ids)},
            ) from exception
        _record_chroma_success("get_collection_items", start)

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
        """Supprime une collection ChromaDB par son nom.

        Args:
            collection_name: Nom de la collection à supprimer.

        Returns:
            Aucune valeur.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant la suppression.
        """
        start = time.perf_counter()
        try:
            self.client.delete_collection(name=collection_name)
        except Exception as exception:
            _record_chroma_error("delete_collection", start)
            raise VectorStoreException(
                message="Impossible de supprimer la collection ChromaDB",
                details={"collection": collection_name},
            ) from exception
        _record_chroma_success("delete_collection", start)

    def delete_items_by_ids(self, collection: Collection, ids: list[str]):
        """Supprime des items ChromaDB par identifiants.

        Args:
            collection: Collection ChromaDB cible.
            ids: Identifiants à supprimer.

        Returns:
            Aucune valeur.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant la suppression.
        """
        if not ids:
            return

        start = time.perf_counter()
        try:
            collection.delete(ids=ids)
        except Exception as exception:
            _record_chroma_error("delete_items", start)
            raise VectorStoreException(
                message="Impossible de supprimer les items ChromaDB",
                details={"item_count": len(ids)},
            ) from exception
        _record_chroma_success("delete_items", start)

    def delete_all_items(self, collection: Collection):
        """Supprime tous les items d'une collection ChromaDB.

        Args:
            collection: Collection ChromaDB cible.

        Returns:
            Aucune valeur.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant la lecture ou suppression.
        """
        all_data = collection.get()
        if all_data["ids"]:
            collection.delete(ids=all_data["ids"])

    def retrieve_chunks(
        self, collection: Collection, query_embedding: list[float], top_k: int
    ) -> list[dict[str, Any]]:
        """Interroge ChromaDB sans filtrage applicatif.

        Args:
            collection: Collection ChromaDB à interroger.
            query_embedding: Embedding de recherche.
            top_k: Nombre maximal de résultats demandés.

        Returns:
            Résultat brut ChromaDB.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant la recherche.
        """
        start = time.perf_counter()
        try:
            response: QueryResult = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas"],
            )
        except Exception as exception:
            _record_chroma_error("query", start)
            raise VectorStoreException(
                message="Erreur ChromaDB lors de la recherche vectorielle",
                details={"top_k": top_k},
            ) from exception
        _record_chroma_success("query", start)

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
        """Récupère, enrichit et filtre les chunks selon la similarité.

        Args:
            collection: Collection ChromaDB à interroger.
            query_embedding: Embedding de recherche.
            top_k: Nombre maximal de résultats demandés à ChromaDB.
            minimum_similarity: Similarité minimale conservée.
            minimum_number_of_chunks: Nombre minimal de chunks à retourner.

        Returns:
            Chunks enrichis, filtrés et triés par similarité décroissante.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant la recherche.
        """
        start = time.perf_counter()
        try:
            retrieved_chunks: QueryResult = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exception:
            _record_chroma_error("query_filtered", start)
            raise VectorStoreException(
                message="Erreur ChromaDB lors de la recherche vectorielle filtrée",
                details={"top_k": top_k, "minimum_similarity": minimum_similarity},
            ) from exception
        _record_chroma_success("query_filtered", start)

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
        """Récupère tous les chunks associés à des chemins de documents.

        Args:
            collection: Collection ChromaDB à interroger.
            paths: Chemins documentaires recherchés.

        Returns:
            Chunks documentaires enrichis et triés par index.

        Raises:
            VectorStoreException: Si ChromaDB échoue pendant une récupération.
        """
        document_chunks: list[RetrievedChunk] = []
        seen_paths: set[str] = set()

        for path in paths:
            if path in seen_paths:
                continue
            seen_paths.add(path)

            start = time.perf_counter()
            try:
                path_chunks = collection.get(
                    where={"path": path},
                    include=["documents", "metadatas"],
                )
            except Exception as exception:
                _record_chroma_error("get_document_chunks", start)
                raise VectorStoreException(
                    message="Erreur ChromaDB lors de la récupération des chunks documentaires",
                    details={"path": path},
                ) from exception
            _record_chroma_success("get_document_chunks", start)

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
        """Filtre des chunks par similarité minimale.

        Args:
            chunks: Chunks enrichis à filtrer.
            minimum_similarity: Similarité minimale conservée.

        Returns:
            Chunks dont la similarité est suffisante.
        """
        return filter_by_similarity(chunks, minimum_similarity)

    def retrieve_related_chunks(
        self,
        chunks: list[RetrievedChunk],
        collection: Collection,
        max_related_links: int,
    ) -> list[RetrievedChunk]:
        """Ajoute des chunks liés à partir des liens internes des métadonnées.

        Args:
            chunks: Chunks sources contenant les liens internes.
            collection: Collection ChromaDB à interroger.
            max_related_links: Nombre maximal de liens documentaires à suivre.

        Returns:
            Chunks d'origine complétés par les chunks liés non dupliqués.

        Raises:
            KeyError: Si les métadonnées de liens attendues sont absentes.
        """

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
    """Fusionne documents, métadonnées et distances en chunks enrichis.

    Args:
        documents: Documents texte retournés par ChromaDB.
        metadatas: Métadonnées associées aux documents.
        distances: Distances vectorielles associées aux documents.

    Returns:
        Chunks enrichis avec distance et similarité.
    """
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
    """Filtre et trie des chunks par similarité minimale.

    Args:
        chunks: Chunks enrichis à filtrer.
        minimum_similarity: Similarité minimale conservée.

    Returns:
        Chunks filtrés triés par similarité décroissante.
    """
    return sorted(
        (chunk for chunk in chunks if chunk["similarity"] >= minimum_similarity),
        key=lambda chunk: chunk["similarity"],
        reverse=True,
    )


def sort_chunks_by_index(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Trie des chunks selon leur index documentaire.

    Args:
        chunks: Chunks à trier.

    Returns:
        Chunks triés par `metadata.chunk_index` croissant.
    """
    return sorted(
        chunks,
        key=lambda chunk: chunk["metadata"].get("chunk_index", 0),
    )


def extract_related_links(chunks: list[RetrievedChunk]) -> dict[str, float]:
    """Extrait les liens internes et leur meilleur score hérité.

    Args:
        chunks: Chunks contenant les métadonnées `has_links` et `related_links`.

    Returns:
        Dictionnaire `path -> score` pour les documents liés.

    Raises:
        KeyError: Si les métadonnées de liens attendues sont absentes.
    """
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


def _record_chroma_success(operation: str, start: float) -> None:
    """Enregistre la durée d'une opération ChromaDB réussie.

    Args:
        operation: Nom stable de l'opération ChromaDB.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    retriever_chroma_duration_seconds.labels(
        operation=operation, status="success"
    ).observe(time.perf_counter() - start)


def _record_chroma_error(operation: str, start: float) -> None:
    """Enregistre la durée d'une opération ChromaDB échouée.

    Args:
        operation: Nom stable de l'opération ChromaDB.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    retriever_chroma_duration_seconds.labels(
        operation=operation, status="error"
    ).observe(time.perf_counter() - start)
