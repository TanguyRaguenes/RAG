from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise tous les codes d'erreur métier du conteneur orchestrator"""

    EMBEDDING_CONTAINER_ERROR = "ERR_EMBEDDING_SERVICE"
    RETRIEVER_CONTAINER_ERROR = "ERR_RETRIEVER_SERVICE"
    RERANKER_CONTAINER_ERROR = "ERR_RERANKER_SERVICE"
    LLM_API_ERROR = "ERR_LLM_API"


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
        """Construit une exception standardisée retournable par l'API orchestrator.

        Args:
            message: Message d'erreur fonctionnel safe à exposer au client API.
            details: Informations non sensibles ajoutées à la réponse d'erreur pour faciliter le diagnostic.
            original_exception: Exception technique d'origine conservée pour le chaînage et le diagnostic.
        """
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convertit l'exception applicative en payload JSON standardisé.

        Returns:
            Payload d'erreur contenant le slug, le message et les détails.
        """
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


class RetrieverContainerException(OrchestratorContainerCustomException):
    """Erreur lors de l'interaction avec le container 'retriever'"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.RETRIEVER_CONTAINER_ERROR


class RerankerContainerException(OrchestratorContainerCustomException):
    """Erreur lors de l'interaction avec le container 'reranker'"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.RERANKER_CONTAINER_ERROR


class LlmApiException(OrchestratorContainerCustomException):
    """Erreur lors de l'interaction avec l'API du LLM"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.LLM_API_ERROR
