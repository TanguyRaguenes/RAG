from typing import Protocol

from app.domain.models.vector_store_model import (
    RetrievedChunk,
    StoredVectorItem,
    VectorStoreBatch,
)


class VectorStoreRepositoryProtocol(Protocol):
    """Définit les opérations de stockage utilisées par les services métier."""

    def count_items(self, collection_name: str) -> int:
        """Retourne le nombre d'items de la collection ciblée."""
        ...

    def list_item_ids(self, collection_name: str) -> list[str]:
        """Retourne tous les identifiants actuellement persistés."""
        ...

    def upsert_items(self, collection_name: str, items: VectorStoreBatch) -> None:
        """Insère ou met à jour un lot d'items vectoriels."""
        ...

    def get_items(self, collection_name: str, ids: list[str]) -> list[StoredVectorItem]:
        """Relit les items correspondant aux identifiants fournis."""
        ...

    def delete_items(self, collection_name: str, ids: list[str]) -> None:
        """Supprime les identifiants fournis sans agir pour une liste vide."""
        ...

    def query_chunks(
        self, collection_name: str, query_embedding: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        """Exécute une recherche vectorielle brute limitée à `top_k`."""
        ...

    def get_chunks_by_paths(
        self, collection_name: str, paths: list[str]
    ) -> list[RetrievedChunk]:
        """Relit les chunks correspondant aux chemins documentaires."""
        ...

    def reset_collection(self, collection_name: str) -> None:
        """Supprime puis recrée une collection vectorielle."""
        ...
