import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# __file__ = chemin du fichier Python courant
_CONFIG_PATH = Path(__file__).parent / "config.json"
RagProvider = Literal["local", "api"]
JudgeProvider = Literal["local", "api"]


class CommonLlmConfig(BaseModel):
    """Paramètres partagés par les fournisseurs du LLM judge."""

    timeout_seconds: float = Field(gt=0)
    stream: bool = False
    temperature: float = Field(ge=0)


class LocalLlmConfig(BaseModel):
    """Configuration du LLM judge local compatible chat completions."""

    provider: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    model: str = Field(min_length=1)
    context_window_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    max_prompt_chars: int = Field(gt=0)


class ApiLlmConfig(BaseModel):
    """Configuration du LLM judge externe compatible Responses API."""

    provider: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    model: str = Field(min_length=1)
    max_output_tokens: int = Field(gt=0)
    max_prompt_chars: int = Field(gt=0)


class LlmConfig(BaseModel):
    """Regroupe les paramètres communs, locaux et API du LLM judge."""

    common: CommonLlmConfig
    local: LocalLlmConfig
    api: ApiLlmConfig


class EvaluatorConfig(BaseModel):
    """Configuration typée du microservice evaluator."""

    llm: LlmConfig
    rag_provider: RagProvider = "api"
    judge_provider: JudgeProvider = "api"


def load_config() -> EvaluatorConfig:
    """Charge le fichier de configuration JSON du microservice.

    Returns:
        Configuration validée du service.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as json_file:
        return EvaluatorConfig.model_validate(json.load(json_file))


def load_admin_groups() -> frozenset[str]:
    """Charge les groupes autorisés à lancer une évaluation.

    Returns:
        Groupes normalisés en minuscules, avec `rag_admin` par défaut.
    """
    raw_groups = os.getenv("RAG_EVALUATOR_ADMIN_GROUPS", "rag_admin")
    groups = frozenset(
        group.strip().casefold() for group in raw_groups.split(",") if group.strip()
    )
    return groups or frozenset({"rag_admin"})
