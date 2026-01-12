from fastapi import FastAPI

from contextlib import asynccontextmanager
from app.core.config import load_config


@asynccontextmanager
async def lifespan(app: FastAPI):

    # startup
    app.state.config = load_config()

    yield

    # shutdown (si besoin plus tard)
    # ex: app.state.vector_store_repository.close()