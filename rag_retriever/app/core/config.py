import json
from pathlib import Path
from typing import Literal, TypedDict, cast

# __file__ = chemin du fichier Python courant
_CONFIG_PATH = Path(__file__).parent / "config.json"


class RetrievalConfig(TypedDict):
    """Règles métier appliquées aux résultats vectoriels."""

    top_k: int
    minimum_similarity: float
    minimum_number_of_chunks: int
    max_related_links: int


CollectionProfile = Literal["default", "evaluation"]


class CollectionsConfig(TypedDict):
    """Associe chaque profil autorisé à une collection ChromaDB fixe."""

    default: str
    evaluation: str


class RetrieverConfig(TypedDict):
    """Configuration applicative complète du retriever."""

    retriever: RetrievalConfig
    collections: CollectionsConfig


def get_collection_name(
    config: RetrieverConfig, collection_profile: CollectionProfile
) -> str:
    """Retourne la collection fixe associée au profil validé.

    Args:
        config: Configuration complète du retriever.
        collection_profile: Profil logique demandé par un service interne.

    Returns:
        Nom de collection ChromaDB configuré pour ce profil.
    """
    return config["collections"][collection_profile]


def load_config() -> RetrieverConfig:
    """Charge le fichier de configuration JSON du microservice.

    Returns:
        Dictionnaire de configuration lu depuis le fichier JSON du service.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as jsonFile:
        return cast(RetrieverConfig, json.load(jsonFile))
