from typing import Literal

from pydantic import BaseModel, Field


class JudgeMessage(BaseModel):
    """Message compatible avec le contrat chat completions."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionMessage(BaseModel):
    """Message retourné par un fournisseur compatible OpenAI."""

    content: str = Field(min_length=1)


class ChatCompletionChoice(BaseModel):
    """Choix de réponse retourné par le juge LLM."""

    message: ChatCompletionMessage


class ChatCompletionResponse(BaseModel):
    """Partie obligatoire de la réponse HTTP chat completions."""

    choices: list[ChatCompletionChoice] = Field(min_length=1)


class ResponsesApiContent(BaseModel):
    """Contenu textuel retourné par l'API Responses."""

    type: str | None = None
    text: str | None = None


class ResponsesApiOutput(BaseModel):
    """Élément de sortie contenant les contenus générés par l'API Responses."""

    type: str | None = None
    content: list[ResponsesApiContent] = Field(default_factory=list)


class ResponsesApiResponse(BaseModel):
    """Partie obligatoire de la réponse HTTP de l'API Responses."""

    output: list[ResponsesApiOutput] = Field(min_length=1)
