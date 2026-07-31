import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from app.api.lifespan import lifespan
from app.api.routers.rerank_router import router as rerank_router
from app.core.exceptions import RerankerContainerCustomException
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging("rag_reranker")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG_RERANKER",
    description="",
    version="1.0.0",
    lifespan=lifespan,
)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(rerank_router)


@app.get("/")
def read_root():
    """Retourne l'état de santé minimal du microservice.

    Returns:
        Payload de healthcheck indiquant que l'API est joignable.
    """
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(RerankerContainerCustomException)
async def reranker_exception_handler(
    request: Request, exception: RerankerContainerCustomException
):
    """Handler centralisé pour les exceptions métier"""
    logger.exception(
        exception.message,
        extra={
            "group": "reranking",
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
