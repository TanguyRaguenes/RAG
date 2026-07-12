from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise les codes d'erreur métier du conteneur evaluator."""

    EVALUATOR_CLIENT_ERROR = "ERR_EVALUATOR_CLIENT"
    DATASET_ERROR = "ERR_DATASET"
    JUDGE_ERROR = "ERR_JUDGE"


class EvaluatorContainerCustomException(Exception):
    """Base exception pour le conteneur evaluator."""

    STATUS_CODE = 500
    SLUG = ErrorSlug.EVALUATOR_CLIENT_ERROR

    def __init__(self, message: str, details: dict | None = None):
        """Initialise une exception métier evaluator.

        Args:
            message: Message lisible décrivant l'erreur.
            details: Métadonnées non sensibles utiles au diagnostic.

        Returns:
            Aucune valeur.
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convertit l'exception en réponse JSON standardisée.

        Returns:
            Dictionnaire contenant le slug, le message et les détails.
        """
        return {
            "slug": self.SLUG.value,
            "message": self.message,
            "details": self.details,
        }


class EvaluatorClientError(EvaluatorContainerCustomException):
    """Erreur lors d'un appel HTTP sortant depuis le service evaluator."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.EVALUATOR_CLIENT_ERROR


class DatasetException(EvaluatorContainerCustomException, ValueError):
    """Erreur lors du chargement ou de la validation du dataset."""

    STATUS_CODE = 422
    SLUG = ErrorSlug.DATASET_ERROR


class JudgeEvaluationException(EvaluatorContainerCustomException):
    """Erreur lors de l'évaluation de réponse par le juge LLM."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.JUDGE_ERROR
