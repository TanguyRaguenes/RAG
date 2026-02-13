from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise tous les codes d'erreur métier du conteneur embedder"""

    EMBEDDING_ERROR = "ERR_EMBEDDING_SERVICE"
    RETRIEVAL_ERROR = "ERR_RETRIEVAL_SERVICE"
    MARKDOWN_PROCESSING = "ERR_MARKDOWN_PROCESSING"


class EmbedderContainerCustomException(Exception):
    """Base exception pour le conteneur embedder"""

    STATUS_CODE = 500
    SLUG = "ERR_INTERNAL"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "slug": self.SLUG.value,
            "message": self.message,
            "details": self.details,
        }


class EmbeddingServiceException(EmbedderContainerCustomException):
    """Erreur lors de l'interaction avec le service 'embedder'"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.EMBEDDING_ERROR


class RetrievalServiceException(EmbedderContainerCustomException):
    """Erreur lors de l'interaction avec le service 'retriever'"""

    STATUS_CODE = 503
    SLUG = ErrorSlug.RETRIEVAL_ERROR


class MarkdownProcessingException(EmbedderContainerCustomException):
    """Erreur lors du traitement des fichiers Markdown"""

    STATUS_CODE = 422
    SLUG = ErrorSlug.MARKDOWN_PROCESSING
