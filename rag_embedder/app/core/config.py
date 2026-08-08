import json
from pathlib import Path
from typing import TypedDict, cast

_CONFIG_PATH = Path(__file__).parent / "config.json"


class EmbeddingPrefixesConfig(TypedDict):
    """Préfixes appliqués aux requêtes et documents avant embedding."""

    query: str
    document: str


class EmbeddingConfig(TypedDict):
    """Configuration du fournisseur d'embeddings."""

    provider: str
    url: str
    model: str
    batch_size: int
    prefixes: EmbeddingPrefixesConfig


class ChunkingConfig(TypedDict):
    """Paramètres de découpage des documents Markdown."""

    size_chars: int
    overlap_chars: int


class EmbedderConfig(TypedDict):
    """Configuration applicative complète de l'embedder."""

    embedding: EmbeddingConfig
    chunking: ChunkingConfig


def load_config() -> EmbedderConfig:
    """Charge le fichier de configuration JSON du microservice.

    Returns:
        Dictionnaire de configuration lu depuis le fichier JSON du service.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as jsonFile:
        return cast(EmbedderConfig, json.load(jsonFile))
