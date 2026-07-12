from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise les codes d'erreur métier du retriever."""

    VECTOR_STORE_ERROR = "ERR_VECTOR_STORE"
    COLLECTION_ERROR = "ERR_COLLECTION"
    RETRIEVAL_FORMAT_ERROR = "ERR_RETRIEVAL_FORMAT"


class RetrieverContainerCustomException(Exception):
    """Base exception pour le conteneur retriever."""

    STATUS_CODE = 500
    SLUG = ErrorSlug.VECTOR_STORE_ERROR

    def __init__(self, message: str, details: dict | None = None):
        """Initialise une exception métier retriever.

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


class VectorStoreException(RetrieverContainerCustomException):
    """Erreur lors d'une opération ChromaDB."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.VECTOR_STORE_ERROR


class CollectionException(RetrieverContainerCustomException):
    """Erreur lors de la gestion d'une collection vectorielle."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.COLLECTION_ERROR


class RetrievalFormatException(RetrieverContainerCustomException):
    """Erreur de format dans les données retournées par le store vectoriel."""

    STATUS_CODE = 502
    SLUG = ErrorSlug.RETRIEVAL_FORMAT_ERROR
