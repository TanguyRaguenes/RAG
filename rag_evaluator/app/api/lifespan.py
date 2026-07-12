from fastapi import FastAPI

from contextlib import asynccontextmanager
from app.core.config import load_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    """Prépare les ressources applicatives au démarrage puis les libère à l'arrêt du service.

    Args:
        app: Application FastAPI dont l'état contient les ressources partagées du service.
    """
    app.state.config = load_config()

    yield

    # shutdown (si besoin plus tard)
    # ex: app.state.vector_store_repository.close()
