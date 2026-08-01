import importlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import load_config
from app.dal.clients.reranking_client import TeiRerankingClient
from app.services.rerank_chunks_service import RerankChunksService


def _warm_up_http_stack() -> None:
    """Précharge httpcore pour éviter un import paresseux sur la première requête."""
    importlib.import_module("httpcore._async.http11")
    importlib.import_module("httpcore._sync.http11")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prépare les ressources applicatives au démarrage puis les libère à l'arrêt du service.

    Args:
        app: Application FastAPI dont l'état contient les ressources partagées du service.
    """
    _warm_up_http_stack()
    app.state.config = load_config()
    app.state.rerank_chunks_service = RerankChunksService(
        config=app.state.config,
        client=TeiRerankingClient(app.state.config.reranking),
    )

    yield
