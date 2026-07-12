from chromadb.api.models.Collection import Collection
from fastapi import Request

from app.dal.repositories.vector_store_repository import VectorStoreRepository


def get_config(request: Request) -> dict:
    """Retourne la configuration chargée au démarrage de l'application FastAPI.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Configuration applicative disponible dans `app.state`.
    """
    return request.app.state.config


def get_vector_store_repository(request: Request) -> VectorStoreRepository:
    """Récupère vector store repository depuis la source adaptée au contexte du service.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Données vector store repository récupérées depuis la source du service.
    """
    return request.app.state.vector_store_repository


def get_wikis_collection(request: Request) -> Collection:
    """Récupère wikis collection depuis la source adaptée au contexte du service.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Données wikis collection récupérées depuis la source du service.
    """
    repository = request.app.state.vector_store_repository
    config = request.app.state.config
    collection_name: str = config["collection"]["name"]
    return repository.get_or_create_collection(collection_name)
