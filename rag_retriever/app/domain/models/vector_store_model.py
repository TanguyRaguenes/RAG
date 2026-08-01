from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VectorMetadata:
    """Représente les métadonnées métier d'un chunk documentaire."""

    path: str
    title: str
    chunk_index: int
    related_links: str = ""
    has_links: bool = False

    def to_storage_dict(self) -> dict[str, str | int | bool]:
        """Convertit les métadonnées vers les primitives acceptées par ChromaDB.

        Returns:
            Dictionnaire sans objet Pydantic ni type spécifique au stockage.
        """
        return {
            "path": self.path,
            "title": self.title,
            "chunk_index": self.chunk_index,
            "related_links": self.related_links,
            "has_links": self.has_links,
        }


@dataclass(frozen=True, slots=True)
class VectorStoreBatch:
    """Regroupe des items vectoriels alignés prêts à être persistés."""

    ids: list[str]
    documents: list[str]
    embeddings: list[list[float]]
    metadatas: list[VectorMetadata]


@dataclass(frozen=True, slots=True)
class StoredVectorItem:
    """Représente un item relu après sa persistance."""

    id: str
    document: str
    metadata: VectorMetadata


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Représente un résultat vectoriel indépendant de ChromaDB."""

    document: str
    metadata: VectorMetadata
    distance: float

    @property
    def similarity(self) -> float:
        """Convertit la distance cosinus ChromaDB en similarité.

        Returns:
            Similarité cosinus, où une valeur élevée indique un meilleur résultat.
        """
        return 1.0 - self.distance
