from pydantic import BaseModel, ConfigDict, Field


class EmbedRequestBase(BaseModel):
    """Décrit les textes reçus par l'endpoint d'embedding."""

    model_config = ConfigDict(extra="forbid")

    texts: list[str] = Field(min_length=1)
