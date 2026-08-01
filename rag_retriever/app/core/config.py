import json
from pathlib import Path
from typing import TypedDict, cast

# __file__ = chemin du fichier Python courant
_CONFIG_PATH = Path(__file__).parent / "config.json"


class RetrievalConfig(TypedDict):
    """Règles métier appliquées aux résultats vectoriels."""

    top_k: int
    minimum_similarity: float
    minimum_number_of_chunks: int
    max_related_links: int


class CollectionConfig(TypedDict):
    """Configuration de la collection ChromaDB active."""

    name: str


class RetrieverConfig(TypedDict):
    """Configuration applicative complète du retriever."""

    retriever: RetrievalConfig
    collection: CollectionConfig


def load_config() -> RetrieverConfig:
    """Charge le fichier de configuration JSON du microservice.

    Returns:
        Dictionnaire de configuration lu depuis le fichier JSON du service.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as jsonFile:
        return cast(RetrieverConfig, json.load(jsonFile))
