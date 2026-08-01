import json
from pathlib import Path

from pydantic import BaseModel, Field

_CONFIG_PATH = Path(__file__).parent / "config.json"


class RerankingConfig(BaseModel):
    """Configuration validée du fournisseur de reranking."""

    provider: str
    url: str
    model: str
    top_k: int = Field(ge=0)
    minimum_rerank_score: float = Field(default=0.005, ge=0, le=1)
    timeout_seconds: float = Field(default=180, gt=0)
    max_chunk_chars: int = Field(default=1600, gt=0)


class RerankerConfig(BaseModel):
    """Configuration typée du microservice reranker."""

    reranking: RerankingConfig


def load_config() -> RerankerConfig:
    """Charge le fichier de configuration JSON du microservice.

    Returns:
        Configuration validée du service.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as json_file:
        return RerankerConfig.model_validate(json.load(json_file))
