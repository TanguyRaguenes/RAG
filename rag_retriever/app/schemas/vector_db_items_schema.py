from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models.vector_store_model import VectorMetadata, VectorStoreBatch


class VectorMetadataBase(BaseModel):
    """Décrit les métadonnées HTTP strictes d'un chunk Markdown."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    title: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    related_links: str = ""
    has_links: bool = False

    def to_domain(self) -> VectorMetadata:
        """Convertit le DTO en modèle métier indépendant de Pydantic.

        Returns:
            Métadonnées utilisables par les services et repositories.
        """
        return VectorMetadata(**self.model_dump())


class VectorStoreItemsBase(BaseModel):
    """Valide un lot vectoriel reçu par l'API de sauvegarde."""

    model_config = ConfigDict(extra="forbid")

    ids: list[str]
    documents: list[str]
    embeddings: list[list[float]]
    metadatas: list[VectorMetadataBase]
    delete_obsolete: bool = False
    replace_collection: bool = False
    include_saved_items: bool = True
    collection_profile: Literal["default", "evaluation"] = "default"

    @model_validator(mode="after")
    def validate_aligned_items(self) -> "VectorStoreItemsBase":
        """Garantit l'alignement et la cohérence dimensionnelle du lot.

        Returns:
            Lot validé lorsque chaque liste décrit exactement les mêmes items.

        Raises:
            ValueError: Si les listes, identifiants ou dimensions sont incohérents.
        """
        item_count = len(self.ids)
        lengths = {
            item_count,
            len(self.documents),
            len(self.embeddings),
            len(self.metadatas),
        }
        if len(lengths) != 1:
            raise ValueError(
                "ids, documents, embeddings and metadatas must have equal lengths"
            )
        if len(set(self.ids)) != item_count:
            raise ValueError("ids must be unique")
        if self.replace_collection and self.collection_profile != "evaluation":
            raise ValueError("replace_collection is restricted to evaluation")
        if self.delete_obsolete and not self.ids:
            raise ValueError("delete_obsolete requires at least one id")
        if self.embeddings:
            dimensions = {len(embedding) for embedding in self.embeddings}
            if 0 in dimensions or len(dimensions) != 1:
                raise ValueError(
                    "embeddings must be non-empty and have equal dimensions"
                )
        return self

    def to_domain(self) -> VectorStoreBatch:
        """Convertit le DTO validé en lot métier.

        Returns:
            Lot vectoriel ne dépendant pas de la couche HTTP.
        """
        return VectorStoreBatch(
            ids=self.ids,
            documents=self.documents,
            embeddings=self.embeddings,
            metadatas=[metadata.to_domain() for metadata in self.metadatas],
        )
