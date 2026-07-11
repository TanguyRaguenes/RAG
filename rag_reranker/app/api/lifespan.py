from contextlib import asynccontextmanager
import importlib

from fastapi import FastAPI

from app.core.config import load_config


def _warm_up_http_stack() -> None:
    """Précharge httpcore pour éviter un import paresseux sur la première requête."""
    importlib.import_module("httpcore._async.http11")
    importlib.import_module("httpcore._sync.http11")


@asynccontextmanager
async def lifespan(app: FastAPI):

    _warm_up_http_stack()
    app.state.config = load_config()

    yield
