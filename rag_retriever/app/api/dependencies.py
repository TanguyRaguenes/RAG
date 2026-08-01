from fastapi import Request

from app.core.config import RetrieverConfig
from app.dal.repositories.vector_store_repository import VectorStoreRepository


def get_config(request: Request) -> RetrieverConfig:
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
