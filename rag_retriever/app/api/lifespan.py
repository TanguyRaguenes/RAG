from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import load_config
from app.dal.repositories.vector_store_repository import VectorStoreRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.state.config = load_config()
    app.state.vector_store_repository = VectorStoreRepository(app.state.config)

    yield

    # shutdown (si besoin plus tard)
    # ex: app.state.vector_store_repository.close()
