import logging

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.lifespan import lifespan
from app.api.routers.collections_router import router as collections_router
from app.core.exceptions import RetrieverContainerCustomException
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG_RETRIEVER", description="", version="1.0.0", lifespan=lifespan)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)
app.mount("/metrics", make_asgi_app())

app.include_router(collections_router)


@app.get("/")
def read_root():
    """Retourne l'état de santé minimal de l'API.

    Returns:
        Dictionnaire indiquant que l'API répond correctement.
    """
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(RetrieverContainerCustomException)
async def retriever_exception_handler(
    request: Request, exception: RetrieverContainerCustomException
) -> JSONResponse:
    """Transforme une exception métier retriever en réponse HTTP standardisée.

    Args:
        request: Requête FastAPI ayant déclenché l'exception.
        exception: Exception métier propagée par le retriever.

    Returns:
        Réponse JSON contenant le slug, le message et les détails d'erreur.
    """
    logger.exception(
        exception.message,
        extra={
            "service": "rag_retriever",
            "group": "retrieval",
            "event": "business_exception",
            "slug": exception.SLUG,
            "path": request.url.path,
            "details": exception.details,
            "status_code": exception.STATUS_CODE,
        },
    )

    return JSONResponse(
        status_code=exception.STATUS_CODE,
        content=exception.to_dict(),
    )
