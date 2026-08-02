import logging
from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorSlug(str, Enum):
    """Centralise tous les codes d'erreur métier du conteneur reranker"""

    INTERNAL_ERROR = "ERR_INTERNAL"
    RERANKING_ERROR = "ERR_RERANKING_SERVICE"
    RERANKING_RESPONSE_FORMAT = "ERR_RERANKING_RESPONSE_FORMAT"


class RerankerContainerCustomException(Exception):
    """Base exception pour le conteneur reranker"""

    STATUS_CODE = 500
    SLUG = ErrorSlug.RERANKING_ERROR

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        internal_message: str | None = None,
        internal_details: dict[str, Any] | None = None,
    ) -> None:
        """Construit une exception standardisée retournable par l'API reranker.

        Args:
            message: Message d'erreur fonctionnel safe à exposer au client API.
            details: Informations non sensibles ajoutées à la réponse d'erreur pour faciliter le diagnostic.
            internal_message: Diagnostic technique réservé aux logs du service.
            internal_details: Métadonnées techniques réservées aux logs du service.
        """
        self.public_message = message
        self.public_details = details or {}
        self.internal_message = internal_message or type(self).__name__
        self.internal_details = internal_details or {}
        self.message = self.public_message
        self.details = self.public_details
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'exception applicative en payload JSON standardisé.

        Returns:
            Payload d'erreur contenant le slug, le message et les détails.
        """
        return {
            "slug": self.SLUG.value,
            "message": self.public_message,
            "details": self.public_details,
        }


class RerankingServiceException(RerankerContainerCustomException):
    """Erreur lors de l'interaction avec le service de reranking"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.RERANKING_ERROR


class RerankingResponseFormatException(RerankerContainerCustomException):
    """Erreur lorsque la réponse du modèle de reranking est invalide"""

    STATUS_CODE = 502
    SLUG = ErrorSlug.RERANKING_RESPONSE_FORMAT


def register_exception_handlers(app: FastAPI) -> None:
    """Enregistre les handlers d'erreurs contrôlées et inattendues.

    Args:
        app: Application FastAPI à laquelle rattacher le contrat d'erreur.
    """
    app.add_exception_handler(
        RerankerContainerCustomException,
        reranker_exception_handler,
    )
    app.add_exception_handler(Exception, unexpected_exception_handler)


def reranker_exception_handler(
    request: Request,
    exception: RerankerContainerCustomException,
) -> JSONResponse:
    """Retourne une erreur applicative sans exposer son contexte interne.

    Args:
        request: Requête ayant déclenché l'erreur contrôlée.
        exception: Erreur applicative contenant les vues publique et interne.

    Returns:
        Réponse conforme au payload stable de l'API.
    """
    log_method = logger.warning if exception.STATUS_CODE < 500 else logger.error
    log_method(
        "Controlled reranker request failure",
        extra={
            "event": "controlled_request_failure",
            "exception_type": type(exception).__name__,
            "internal_message": exception.internal_message,
            "internal_details": exception.internal_details,
            "path": request.url.path,
            "slug": exception.SLUG.value,
            "status_code": exception.STATUS_CODE,
        },
    )
    return JSONResponse(
        status_code=exception.STATUS_CODE,
        content=exception.to_dict(),
    )


def unexpected_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Masque une erreur inattendue derrière un payload 500 neutre.

    Args:
        request: Requête ayant déclenché le défaut inattendu.
        exception: Exception technique journalisée avec sa trace côté serveur.

    Returns:
        Réponse 500 ne contenant aucun détail de l'exception.
    """
    logger.exception(
        "Unexpected reranker request failure",
        exc_info=(type(exception), exception, exception.__traceback__),
        extra={
            "event": "unexpected_request_failure",
            "exception_type": type(exception).__name__,
            "path": request.url.path,
            "status_code": 500,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "slug": ErrorSlug.INTERNAL_ERROR.value,
            "message": "Une erreur interne est survenue",
            "details": {},
        },
    )
