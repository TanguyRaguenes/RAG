import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from app.api.lifespan import lifespan
from app.api.routers.collections_router import router as collections_router
from app.core.exceptions import ApplicationError, ErrorSlug
from app.core.logging import configure_json_logging
from app.core.telemetry import configure_telemetry

configure_json_logging("rag_retriever")
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG_RETRIEVER", description="", version="1.0.0", lifespan=lifespan)

configure_telemetry()
FastAPIInstrumentor.instrument_app(app)
app.mount("/metrics", make_asgi_app())

app.include_router(collections_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Retourne l'état de santé minimal de l'API.

    Returns:
        Dictionnaire indiquant que l'API répond correctement.
    """
    return {"status": "ok", "message": "API connection successful"}


@app.exception_handler(ApplicationError)
async def retriever_exception_handler(
    request: Request, exception: ApplicationError
) -> JSONResponse:
    """Transforme une exception métier retriever en réponse HTTP standardisée.

    Args:
        request: Requête FastAPI ayant déclenché l'exception.
        exception: Exception métier propagée par le retriever.

    Returns:
        Réponse JSON contenant le slug, le message et les détails d'erreur.
    """
    log_method = logger.warning if exception.STATUS_CODE < 500 else logger.exception
    log_method(
        "Application request failed",
        extra={
            "service": "rag_retriever",
            "group": "retrieval",
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
    """Masque une erreur inattendue derrière un payload HTTP neutre.

    Args:
        request: Requête ayant déclenché l'erreur inattendue.
        exception: Erreur brute réservée à la trace serveur.

    Returns:
        Réponse HTTP 500 conforme au contrat d'erreur commun.
    """
    logger.exception(
        "Unexpected application error",
        extra={
            "service": "rag_retriever",
            "group": "retrieval",
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
