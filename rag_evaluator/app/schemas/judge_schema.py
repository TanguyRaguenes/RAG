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
