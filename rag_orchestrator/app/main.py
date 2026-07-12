import logging

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.lifespan import lifespan
from app.api.routers.auth_router import router as auth_router
from app.api.routers.query_router import router as query_router
from app.api.routers.usage_router import router as usage_router
from app.core.exceptions import OrchestratorContainerCustomException
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging()

app = FastAPI(
    title="RAG_ORCHESTRATOR", description="", version="1.0.0", lifespan=lifespan
)

logger = logging.getLogger(__name__)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)
app.mount("/metrics", make_asgi_app())

app.include_router(query_router)
app.include_router(auth_router)
app.include_router(usage_router)


@app.get("/")
def read_root():
    """Retourne l'état de santé minimal de l'API.

    Returns:
        Dictionnaire indiquant que l'API répond correctement.
    """
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(OrchestratorContainerCustomException)
async def embedder_exception_handler(
    request: Request, exception: OrchestratorContainerCustomException
):
    """Transforme une exception métier en réponse HTTP standardisée.

    Args:
        request: Requête FastAPI ayant déclenché l'exception.
        exception: Exception métier propagée par le service.

    Returns:
        Réponse JSON contenant le slug, le message et les détails d'erreur.
    """
    logger.exception(
        exception.message,
        extra={
            "service": "rag_orchestrator",
            "group": "orchestration",
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
