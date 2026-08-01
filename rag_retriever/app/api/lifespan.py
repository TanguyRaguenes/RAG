from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import load_config
from app.dal.repositories.vector_store_repository import VectorStoreRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prépare les ressources applicatives au démarrage puis les libère à l'arrêt du service.

    Args:
        app: Application FastAPI dont l'état contient les ressources partagées du service.
    """
    app.state.config = load_config()
    app.state.vector_store_repository = VectorStoreRepository()

    yield
