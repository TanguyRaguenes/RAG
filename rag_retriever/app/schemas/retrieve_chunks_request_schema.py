from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CollectionProfile = Literal["default", "evaluation"]


class RetrieveChunksRequestBase(BaseModel):
    """Décrit une recherche de chunks à partir d'un embedding."""

    model_config = ConfigDict(extra="forbid")

    embeded_question: list[float] = Field(min_length=1)
    collection_profile: CollectionProfile = "default"


class RetrieveDocumentChunksRequestBase(BaseModel):
    """Décrit les chemins dont tous les chunks doivent être relus."""

    model_config = ConfigDict(extra="forbid")

    paths: list[str]
    collection_profile: CollectionProfile = "default"
