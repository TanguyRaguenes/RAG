import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from app.api.lifespan import lifespan
from app.api.routers.embed_router import router as embed_router
from app.core.exceptions import ApplicationError, ErrorSlug
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging("rag_embedder")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG_EMBEDDER",
    description="",
    version="1.0.0",
    lifespan=lifespan,
)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(embed_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Retourne l'état de santé minimal du microservice.

    Returns:
        Payload de healthcheck indiquant que l'API est joignable.
    """
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(ApplicationError)
async def embedder_exception_handler(
    request: Request, exception: ApplicationError
) -> JSONResponse:
    """Journalise une fois puis expose le contrat public de l'erreur.

    Args:
        request: Requête ayant déclenché l'erreur applicative.
        exception: Erreur typée contenant un diagnostic réservé au serveur.

    Returns:
        Réponse stable ne contenant aucun détail interne.
    """
    log_method = logger.warning if exception.STATUS_CODE < 500 else logger.exception
    log_method(
        "Application request failed",
        extra={
            "group": "embedding",
            "event": "application_error",
            "slug": exception.SLUG.value,
            "path": request.url.path,
            "internal_details": exception.internal_details,
            "status_code": exception.STATUS_CODE,
        },
    )

    return JSONResponse(
        status_code=exception.STATUS_CODE,
        content=exception.to_dict(),
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    """Masque et journalise une erreur inattendue.

    Args:
        request: Requête ayant déclenché l'erreur inattendue.
        exception: Erreur brute conservée uniquement dans la trace serveur.

    Returns:
        Réponse HTTP 500 neutre au même format que les erreurs applicatives.
    """
    logger.exception(
        "Unexpected application error",
        extra={
            "group": "embedding",
            "event": "unexpected_error",
            "path": request.url.path,
            "error_type": type(exception).__name__,
            "status_code": 500,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "slug": ErrorSlug.INTERNAL.value,
            "message": ApplicationError.PUBLIC_MESSAGE,
            "details": {},
        },
    )
