from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise tous les codes d'erreur métier du conteneur orchestrator"""

    EMBEDDING_CONTAINER_ERROR = "ERR_EMBEDDING_SERVICE"


class OrchestratorContainerCustomException(Exception):
    """Base exception pour le conteneur orchestrator"""

    STATUS_CODE = 500
    SLUG = "ERR_INTERNAL"

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        original_exception: dict | None = None,
    ):
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        super().__init__(message)

    def to_dict(self) -> dict:

        informations: dict = {
            "slug": self.SLUG.value,
            "message": self.message,
            "details": self.details,
        }

        if self.original_exception:
            informations["original_exception"] = {
                "slug": self.original_exception["slug"],
                "message": self.original_exception["message"],
                "details": self.original_exception["details"],
            }

        return informations


class EmbedderContainerException(OrchestratorContainerCustomException):
    """Erreur lors de l'interaction avec le container 'embedder'"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.EMBEDDING_CONTAINER_ERROR
