import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# __file__ = chemin du fichier Python courant
_CONFIG_PATH = Path(__file__).parent / "config.json"
RagProvider = Literal["local", "api"]


class LlmConfig(BaseModel):
    """Configuration commune aux fournisseurs de juge LLM."""

    provider: str
    url_provider: str
    model: str
    temperature: float = Field(ge=0)
    num_ctx: int = Field(gt=0)
    max_output_token: int = Field(gt=0)
    timeout_seconds: float = Field(gt=0)
    stream: bool = False


class EvaluationMethodConfig(BaseModel):
    """Sélectionne le fournisseur utilisé pour juger les réponses."""

    use_api_openai: bool = False
    openai_url: str = Field(
        default="https://api.openai.com/v1/chat/completions",
        min_length=1,
    )
    openai_model: str = Field(default="gpt-4o", min_length=1)


class EvaluatorConfig(BaseModel):
    """Configuration typée du microservice evaluator."""

    llm: LlmConfig
    evaluation_method: EvaluationMethodConfig
    rag_provider: RagProvider = "api"


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
