import logging
from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorSlug(str, Enum):
    """Centralise les codes d'erreur métier du conteneur evaluator."""

    INTERNAL_ERROR = "ERR_INTERNAL"
    EVALUATOR_CLIENT_ERROR = "ERR_EVALUATOR_CLIENT"
    AUTHENTICATION_ERROR = "ERR_EVALUATOR_AUTHENTICATION"
    AUTHORIZATION_ERROR = "ERR_EVALUATOR_AUTHORIZATION"
    DATASET_ERROR = "ERR_DATASET"
    JUDGE_ERROR = "ERR_JUDGE"


class EvaluatorContainerCustomException(Exception):
    """Base exception pour le conteneur evaluator."""

    STATUS_CODE = 500
    SLUG = ErrorSlug.EVALUATOR_CLIENT_ERROR

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        internal_message: str | None = None,
        internal_details: dict[str, Any] | None = None,
    ) -> None:
        """Initialise une exception métier evaluator.

        Args:
            message: Message lisible décrivant l'erreur.
            details: Métadonnées non sensibles utiles au diagnostic.
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
        """Convertit l'exception en réponse JSON standardisée.

        Returns:
            Dictionnaire contenant le slug, le message et les détails.
        """
        return {
            "slug": self.SLUG.value,
            "message": self.public_message,
            "details": self.public_details,
        }


class EvaluatorClientError(EvaluatorContainerCustomException):
    """Erreur lors d'un appel HTTP sortant depuis le service evaluator."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.EVALUATOR_CLIENT_ERROR


class EvaluatorAuthenticationError(EvaluatorContainerCustomException):
    """Erreur lorsque le bearer est absent, invalide ou refusé."""

    STATUS_CODE = 401
    SLUG = ErrorSlug.AUTHENTICATION_ERROR


class EvaluatorAuthorizationError(EvaluatorContainerCustomException):
    """Erreur lorsque l'identité n'appartient à aucun groupe administrateur."""

    STATUS_CODE = 403
    SLUG = ErrorSlug.AUTHORIZATION_ERROR


class DatasetException(EvaluatorContainerCustomException, ValueError):
    """Erreur lors du chargement ou de la validation du dataset."""

    STATUS_CODE = 422
    SLUG = ErrorSlug.DATASET_ERROR


class JudgeEvaluationException(EvaluatorContainerCustomException):
    """Erreur lors de l'évaluation de réponse par le juge LLM."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.JUDGE_ERROR


def register_exception_handlers(app: FastAPI) -> None:
    """Enregistre les handlers d'erreurs contrôlées et inattendues.

    Args:
        app: Application FastAPI à laquelle rattacher le contrat d'erreur.
    """
    app.add_exception_handler(
        EvaluatorContainerCustomException,
        evaluator_exception_handler,
    )
    app.add_exception_handler(Exception, unexpected_exception_handler)


async def evaluator_exception_handler(
    request: Request,
    exception: EvaluatorContainerCustomException,
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
        "Controlled evaluator request failure",
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
    headers = {"WWW-Authenticate": "Bearer"} if exception.STATUS_CODE == 401 else None
    return JSONResponse(
        status_code=exception.STATUS_CODE,
        content=exception.to_dict(),
        headers=headers,
    )


async def unexpected_exception_handler(
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
        "Unexpected evaluator request failure",
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
