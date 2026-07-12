from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise tous les codes d'erreur métier du conteneur reranker"""

    RERANKING_ERROR = "ERR_RERANKING_SERVICE"
    RERANKING_RESPONSE_FORMAT = "ERR_RERANKING_RESPONSE_FORMAT"


class RerankerContainerCustomException(Exception):
    """Base exception pour le conteneur reranker"""

    STATUS_CODE = 500
    SLUG = "ERR_INTERNAL"

    def __init__(self, message: str, details: dict | None = None):
        """Construit une exception standardisée retournable par l'API reranker.

        Args:
            message: Message d'erreur fonctionnel safe à exposer au client API.
            details: Informations non sensibles ajoutées à la réponse d'erreur pour faciliter le diagnostic.
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convertit l'exception applicative en payload JSON standardisé.

        Returns:
            Payload d'erreur contenant le slug, le message et les détails.
        """
        return {
            "slug": self.SLUG.value,
            "message": self.message,
            "details": self.details,
        }


class RerankingServiceException(RerankerContainerCustomException):
    """Erreur lors de l'interaction avec le service de reranking"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.RERANKING_ERROR


class RerankingResponseFormatException(RerankerContainerCustomException):
    """Erreur lorsque la réponse du modèle de reranking est invalide"""

    STATUS_CODE = 502
    SLUG = ErrorSlug.RERANKING_RESPONSE_FORMAT
