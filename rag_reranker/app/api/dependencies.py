from typing import Annotated

from fastapi import Depends, Request

from app.core.config import RerankerConfig
from app.services.rerank_chunks_service import RerankChunksService


def get_config(request: Request) -> RerankerConfig:
    """Retourne la configuration chargée au démarrage de l'application FastAPI.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Configuration applicative disponible dans `app.state`.
    """
    return request.app.state.config


def get_rerank_chunks_service(request: Request) -> RerankChunksService:
    """Retourne le service de reranking construit au démarrage.

    Args:
        request: Requête FastAPI donnant accès à l'état applicatif.

    Returns:
        Service injecté avec son client externe.
    """
    return request.app.state.rerank_chunks_service


RerankServiceDep = Annotated[RerankChunksService, Depends(get_rerank_chunks_service)]
