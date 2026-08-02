import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError, ErrorSlug

logger = logging.getLogger(__name__)


def application_exception_handler(
    request: Request, exception: ApplicationError
) -> JSONResponse:
    """Transforme une erreur contrôlée en réponse publique standardisée.

    Args:
        request: Requête FastAPI ayant déclenché l'exception.
        exception: Erreur applicative propagée par le service.

    Returns:
        Réponse JSON ne contenant que le contrat public de l'erreur.
    """
    log_context = {
        "service": "rag_orchestrator",
        "event": "application_error",
        "error_type": type(exception).__name__,
        "slug": exception.SLUG.value,
        "path": request.url.path,
        "status_code": exception.STATUS_CODE,
    }
    if exception.STATUS_CODE < 500:
        logger.warning("Expected application error", extra=log_context)
    else:
        logger.error("Handled infrastructure error", extra=log_context)

    return JSONResponse(
        status_code=exception.STATUS_CODE,
        content=exception.to_public_dict(),
    )


def unexpected_exception_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    """Retourne un 500 neutre et journalise une seule fois l'erreur inattendue.

    Args:
        request: Requête FastAPI ayant déclenché l'exception.
        exception: Erreur non contrôlée propagée jusqu'à la frontière ASGI.

    Returns:
        Réponse JSON 500 ne contenant aucune donnée issue de l'exception.
    """
    logger.exception(
        "Unhandled application error",
        exc_info=(type(exception), exception, exception.__traceback__),
        extra={
            "service": "rag_orchestrator",
            "event": "unexpected_error",
            "error_type": type(exception).__name__,
            "slug": ErrorSlug.INTERNAL.value,
            "path": request.url.path,
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
