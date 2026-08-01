from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise les codes d'erreur publics du conteneur embedder."""

    INTERNAL = "ERR_INTERNAL"
    EMBEDDING_ERROR = "ERR_EMBEDDING_SERVICE"
    RETRIEVAL_ERROR = "ERR_RETRIEVAL_SERVICE"
    MARKDOWN_PROCESSING = "ERR_MARKDOWN_PROCESSING"


class ApplicationError(Exception):
    """Sépare le contrat d'erreur public du diagnostic interne."""

    STATUS_CODE = 500
    SLUG = ErrorSlug.INTERNAL
    PUBLIC_MESSAGE = "Une erreur interne est survenue."

    def __init__(self, internal_details: dict[str, object] | None = None) -> None:
        """Construit une erreur applicative sans exposer son contexte technique.

        Args:
            internal_details: Contexte réservé à la journalisation côté serveur.
        """
        self.message = self.PUBLIC_MESSAGE
        self.internal_details = internal_details or {}
        super().__init__(self.PUBLIC_MESSAGE)

    def to_dict(self) -> dict[str, object]:
        """Convertit l'exception applicative en payload JSON standardisé.

        Returns:
            Payload d'erreur contenant le slug, le message et les détails.
        """
        return {
            "slug": self.SLUG.value,
            "message": self.PUBLIC_MESSAGE,
            "details": {},
        }


class EmbeddingServiceException(ApplicationError):
    """Signale une indisponibilité ou une réponse invalide du fournisseur."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.EMBEDDING_ERROR
    PUBLIC_MESSAGE = "Le service d'embeddings est temporairement indisponible."


class RetrievalServiceException(ApplicationError):
    """Signale un échec de communication avec le stockage vectoriel."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.RETRIEVAL_ERROR
    PUBLIC_MESSAGE = "Le service de stockage est temporairement indisponible."


class MarkdownProcessingException(ApplicationError):
    """Signale qu'un document Markdown ne peut pas être traité sûrement."""

    STATUS_CODE = 422
    SLUG = ErrorSlug.MARKDOWN_PROCESSING
    PUBLIC_MESSAGE = "Les documents Markdown n'ont pas pu être traités."
