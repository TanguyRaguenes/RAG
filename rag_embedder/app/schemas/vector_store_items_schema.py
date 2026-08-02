from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CollectionProfile = Literal["default", "evaluation"]


class VectorMetadataBase(BaseModel):
    """Décrit les métadonnées stables associées à un chunk Markdown."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    title: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    related_links: str = ""
    has_links: bool = False


class VectorStoreItemsBase(BaseModel):
    """Valide un lot vectoriel envoyé au service retriever."""

    model_config = ConfigDict(extra="forbid")

    ids: list[str]
    documents: list[str]
    embeddings: list[list[float]]
    metadatas: list[VectorMetadataBase]
    delete_obsolete: bool = False
    replace_collection: bool = False
    collection_profile: CollectionProfile = "default"

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
        if self.embeddings:
            dimensions = {len(embedding) for embedding in self.embeddings}
            if 0 in dimensions or len(dimensions) != 1:
                raise ValueError(
                    "embeddings must be non-empty and have equal dimensions"
                )
        return self
