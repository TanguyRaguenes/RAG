from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import load_config


@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.config = load_config()

    yield
