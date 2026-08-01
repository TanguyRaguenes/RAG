from pydantic import BaseModel, ConfigDict, Field


class LocalLlmMessage(BaseModel):
    """Message textuel retourné par un LLM local compatible chat completions."""

    model_config = ConfigDict(extra="ignore")
    content: str = Field(min_length=1)


class LocalLlmChoice(BaseModel):
    """Choix de génération contenant le message produit par le LLM local."""

    model_config = ConfigDict(extra="ignore")
    message: LocalLlmMessage


class LocalLlmResponse(BaseModel):
    """Réponse minimale validée attendue du endpoint LLM local."""

    model_config = ConfigDict(extra="ignore")
    choices: list[LocalLlmChoice] = Field(min_length=1)


class ApiLlmUsage(BaseModel):
    """Compteurs de tokens retournés par l'API LLM externe."""

    model_config = ConfigDict(extra="ignore")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ApiLlmContentItem(BaseModel):
    """Élément de contenu susceptible de porter le texte généré."""

    model_config = ConfigDict(extra="ignore")
    type: str | None = None
    text: str | None = None


class ApiLlmOutputItem(BaseModel):
    """Élément de sortie nommé plutôt qu'identifié par une position fixe."""

    model_config = ConfigDict(extra="ignore")
    type: str | None = None
    content: list[ApiLlmContentItem] = Field(default_factory=list)


class ApiLlmResponse(BaseModel):
    """Réponse minimale validée attendue de l'API LLM externe."""

    model_config = ConfigDict(extra="ignore")
    output: list[ApiLlmOutputItem] = Field(min_length=1)
    usage: ApiLlmUsage
