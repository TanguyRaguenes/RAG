import time
from collections.abc import Callable
from numbers import Real
from typing import Any, TypeVar

import chromadb
import httpx
from chromadb.api.models.Collection import Collection
from chromadb.errors import ChromaError

from app.core.exceptions import RetrievalFormatException, VectorStoreException
from app.core.metrics import retriever_chroma_duration_seconds
from app.domain.models.vector_store_model import (
    RetrievedChunk,
    StoredVectorItem,
    VectorMetadata,
    VectorStoreBatch,
)

T = TypeVar("T")


class VectorStoreRepository:
    """Encapsule tous les détails ChromaDB derrière un contrat métier stable."""

    def __init__(self, host: str = "chroma", port: int = 8000) -> None:
        """Initialise le client HTTP ChromaDB.

        Args:
            host: Nom DNS ou hôte du serveur ChromaDB.
            port: Port HTTP du serveur ChromaDB.
        """
        try:
            self._client = chromadb.HttpClient(host=host, port=port)
        except (ChromaError, httpx.HTTPError) as exception:
            raise VectorStoreException(
                internal_details={
                    "operation": "create_client",
                    "error_type": type(exception).__name__,
                },
            ) from exception

    def count_items(self, collection_name: str) -> int:
        """Compte les items d'une collection.

        Args:
            collection_name: Nom de la collection à compter.

        Returns:
            Nombre d'items actuellement persistés.
        """
        count = self._execute(
            "count",
            lambda: self._get_collection(collection_name).count(),
            {"operation": "count"},
        )
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise RetrievalFormatException(
                internal_details={"operation": "count", "reason": "invalid_count"}
            )
        return count

    def list_item_ids(self, collection_name: str) -> list[str]:
        """Liste les identifiants d'une collection.

        Args:
            collection_name: Nom de la collection à parcourir.

        Returns:
            Identifiants persistés, sans exposer la réponse ChromaDB.
        """
        data = self._execute(
            "list_ids",
            lambda: self._get_collection(collection_name).get(include=[]),
            {"operation": "list_ids"},
        )
        try:
            ids = _require_list(data, "ids")
            if not all(isinstance(item_id, str) for item_id in ids):
                raise TypeError("ids must contain strings")
            return ids
        except (KeyError, TypeError, ValueError) as exception:
            raise RetrievalFormatException(
                internal_details={"operation": "list_ids"}
            ) from exception

    def upsert_items(self, collection_name: str, items: VectorStoreBatch) -> None:
        """Insère ou met à jour un lot vectoriel dans une collection.

        Args:
            collection_name: Nom de la collection d'écriture.
            items: Lot métier déjà validé par la couche HTTP.
        """
        if not items.ids:
            return
        self._execute(
            "upsert",
            lambda: self._get_collection(collection_name).upsert(
                ids=items.ids,
                documents=items.documents,
                embeddings=items.embeddings,
                metadatas=[metadata.to_storage_dict() for metadata in items.metadatas],
            ),
            {"item_count": len(items.ids)},
        )

    def get_items(self, collection_name: str, ids: list[str]) -> list[StoredVectorItem]:
        """Relit des items persistés à partir de leurs identifiants.

        Args:
            collection_name: Nom de la collection source.
            ids: Identifiants à relire.

        Returns:
            Items métier reconstruits depuis la réponse ChromaDB.
        """
        if not ids:
            return []
        data = self._execute(
            "get_items",
            lambda: self._get_collection(collection_name).get(
                ids=ids, include=["documents", "metadatas"]
            ),
            {"item_count": len(ids)},
        )
        try:
            ids = _require_list(data, "ids")
            documents = _require_list(data, "documents")
            metadatas = _require_list(data, "metadatas")
            return [
                StoredVectorItem(
                    id=_require_string(item_id, "id"),
                    document=_require_string(document, "document"),
                    metadata=_metadata_from_storage(metadata),
                )
                for item_id, document, metadata in zip(
                    ids,
                    documents,
                    metadatas,
                    strict=True,
                )
            ]
        except (KeyError, TypeError, ValueError) as exception:
            raise RetrievalFormatException(
                internal_details={"operation": "get_items"},
            ) from exception

    def delete_items(self, collection_name: str, ids: list[str]) -> None:
        """Supprime une liste d'items d'une collection.

        Args:
            collection_name: Nom de la collection cible.
            ids: Identifiants à supprimer ; une liste vide est ignorée.
        """
        if not ids:
            return
        self._execute(
            "delete_items",
            lambda: self._get_collection(collection_name).delete(ids=ids),
            {"item_count": len(ids)},
        )

    def query_chunks(
        self, collection_name: str, query_embedding: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        """Interroge ChromaDB sans appliquer de règle de classement métier.

        Args:
            collection_name: Nom de la collection à interroger.
            query_embedding: Vecteur représentant la question utilisateur.
            top_k: Nombre maximal de résultats demandé au moteur vectoriel.

        Returns:
            Résultats métier contenant document, métadonnées et distance.
        """
        data = self._execute(
            "query",
            lambda: self._get_collection(collection_name).query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            ),
            {"top_k": top_k},
        )
        try:
            documents = _require_single_batch(data, "documents")
            metadatas = _require_single_batch(data, "metadatas")
            distances = _require_single_batch(data, "distances")
            return _build_retrieved_chunks(documents, metadatas, distances)
        except (KeyError, IndexError, TypeError, ValueError) as exception:
            raise RetrievalFormatException(
                internal_details={"operation": "query"},
            ) from exception

    def get_chunks_by_paths(
        self, collection_name: str, paths: list[str]
    ) -> list[RetrievedChunk]:
        """Relit les chunks associés à plusieurs chemins en une requête.

        Args:
            collection_name: Nom de la collection source.
            paths: Chemins documentaires dédupliqués par le service métier.

        Returns:
            Chunks correspondants dans l'ordre fourni par ChromaDB.
        """
        if not paths:
            return []
        where: dict[str, Any]
        if len(paths) == 1:
            where = {"path": paths[0]}
        else:
            where = {"path": {"$in": paths}}
        data = self._execute(
            "get_document_chunks",
            lambda: self._get_collection(collection_name).get(
                where=where,
                include=["documents", "metadatas"],
            ),
            {"path_count": len(paths)},
        )
        try:
            documents = _require_list(data, "documents")
            metadatas = _require_list(data, "metadatas")
            return _build_retrieved_chunks(
                documents,
                metadatas,
                [0.0] * len(documents),
            )
        except (KeyError, TypeError, ValueError) as exception:
            raise RetrievalFormatException(
                internal_details={"operation": "get_document_chunks"},
            ) from exception

    def reset_collection(self, collection_name: str) -> None:
        """Supprime puis recrée une collection avec la distance cosinus.

        Args:
            collection_name: Nom de la collection à réinitialiser.
        """
        self._execute(
            "delete_collection",
            lambda: self._client.delete_collection(name=collection_name),
            {"operation": "delete_collection"},
        )
        self._get_collection(collection_name)

    def _get_collection(self, collection_name: str) -> Collection:
        """Récupère la collection technique sans la faire sortir du DAL.

        Args:
            collection_name: Nom de la collection à récupérer ou créer.

        Returns:
            Collection ChromaDB réservée à l'implémentation du repository.
        """
        return self._execute(
            "get_or_create_collection",
            lambda: self._client.get_or_create_collection(
                name=collection_name,
                configuration={"hnsw": {"space": "cosine"}},
            ),
            {"operation": "get_or_create_collection"},
        )

    def _execute(
        self,
        operation: str,
        action: Callable[[], T],
        details: dict[str, Any],
    ) -> T:
        """Exécute et mesure une opération ChromaDB de façon uniforme.

        Args:
            operation: Nom stable utilisé par les métriques.
            action: Appel ChromaDB à exécuter.
            details: Contexte non sensible joint à l'exception applicative.

        Returns:
            Valeur brute immédiatement consommée dans le DAL.

        Raises:
            VectorStoreException: Si l'appel ChromaDB échoue.
        """
        start = time.perf_counter()
        try:
            result = action()
        except (ChromaError, httpx.HTTPError) as exception:
            _record_chroma_duration(operation, "error", start)
            raise VectorStoreException(
                internal_details={
                    **details,
                    "error_type": type(exception).__name__,
                }
            ) from exception
        _record_chroma_duration(operation, "success", start)
        return result


def _metadata_from_storage(metadata: object) -> VectorMetadata:
    """Valide les métadonnées provenant de ChromaDB.

    Args:
        metadata: Valeur technique retournée par ChromaDB.

    Returns:
        Métadonnées métier strictement typées.
    """
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dictionary")
    path = _require_string(metadata["path"], "path")
    title = _require_string(metadata["title"], "title")
    chunk_index = metadata["chunk_index"]
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, int):
        raise TypeError("chunk_index must be an integer")
    related_links = metadata.get("related_links", "")
    has_links = metadata.get("has_links", False)
    if not isinstance(related_links, str) or not isinstance(has_links, bool):
        raise TypeError("optional metadata fields have invalid types")
    return VectorMetadata(
        path=path,
        title=title,
        chunk_index=chunk_index,
        related_links=related_links,
        has_links=has_links,
    )


def _build_retrieved_chunks(
    documents: list[Any],
    metadatas: list[Any],
    distances: list[Any],
) -> list[RetrievedChunk]:
    """Transforme des listes ChromaDB parallèles en résultats métier.

    Args:
        documents: Textes retournés par le stockage.
        metadatas: Métadonnées associées aux textes.
        distances: Distances cosinus associées aux textes.

    Returns:
        Résultats indépendants de la structure de réponse ChromaDB.

    Raises:
        ValueError: Si les listes ne sont pas alignées.
    """
    return [
        _build_retrieved_chunk(document, metadata, distance)
        for document, metadata, distance in zip(
            documents, metadatas, distances, strict=True
        )
    ]


def _build_retrieved_chunk(
    document: object, metadata: object, distance: object
) -> RetrievedChunk:
    """Valide les primitives d'un résultat ChromaDB.

    Args:
        document: Contenu textuel brut du résultat.
        metadata: Métadonnées brutes associées au document.
        distance: Distance cosinus brute retournée par ChromaDB.

    Returns:
        Chunk métier strictement typé.

    Raises:
        TypeError: Si un champ ne respecte pas le contrat Chroma attendu.
    """
    if isinstance(distance, bool) or not isinstance(distance, Real):
        raise TypeError("distance must be a real number")
    return RetrievedChunk(
        document=_require_string(document, "document"),
        metadata=_metadata_from_storage(metadata),
        distance=float(distance),
    )


def _require_list(data: object, key: str) -> list[Any]:
    """Extrait une liste obligatoire d'une réponse ChromaDB.

    Args:
        data: Réponse brute supposée être un dictionnaire.
        key: Champ obligatoire à extraire.

    Returns:
        Liste portée par le champ demandé.

    Raises:
        TypeError: Si la réponse ou le champ n'est pas une liste.
        KeyError: Si le champ demandé est absent.
    """
    if not isinstance(data, dict):
        raise TypeError("Chroma response must be a dictionary")
    value = data[key]
    if not isinstance(value, list):
        raise TypeError(f"{key} must be a list")
    return value


def _require_single_batch(data: object, key: str) -> list[Any]:
    """Extrait l'unique lot d'une réponse de requête ChromaDB.

    Args:
        data: Réponse brute de `Collection.query`.
        key: Champ parallèle à valider.

    Returns:
        Premier et unique lot de résultats.

    Raises:
        ValueError: Si Chroma retourne zéro ou plusieurs lots.
        TypeError: Si le lot n'est pas une liste.
    """
    batches = _require_list(data, key)
    if len(batches) != 1:
        raise ValueError(f"{key} must contain exactly one batch")
    batch = batches[0]
    if not isinstance(batch, list):
        raise TypeError(f"{key} batch must be a list")
    return batch


def _require_string(value: object, field: str) -> str:
    """Valide une chaîne obligatoire issue de ChromaDB.

    Args:
        value: Valeur brute à contrôler.
        field: Nom du champ utilisé dans l'erreur interne.

    Returns:
        Chaîne validée.

    Raises:
        TypeError: Si la valeur n'est pas une chaîne.
    """
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    return value


def _record_chroma_duration(operation: str, status: str, start: float) -> None:
    """Enregistre la durée d'une opération ChromaDB.

    Args:
        operation: Nom stable de l'opération ChromaDB.
        status: Résultat `success` ou `error`.
        start: Instant initial issu de `perf_counter`.
    """
    retriever_chroma_duration_seconds.labels(
        operation=operation, status=status
    ).observe(time.perf_counter() - start)
