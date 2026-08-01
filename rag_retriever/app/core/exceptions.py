from enum import Enum


class ErrorSlug(str, Enum):
    """Centralise les codes d'erreur métier du retriever."""

    INTERNAL = "ERR_INTERNAL"
    VECTOR_STORE_ERROR = "ERR_VECTOR_STORE"
    COLLECTION_ERROR = "ERR_COLLECTION"
    RETRIEVAL_FORMAT_ERROR = "ERR_RETRIEVAL_FORMAT"


class ApplicationError(Exception):
    """Sépare le contrat d'erreur public du diagnostic interne."""

    STATUS_CODE = 500
    SLUG = ErrorSlug.INTERNAL
    PUBLIC_MESSAGE = "Une erreur interne est survenue."

    def __init__(self, internal_details: dict[str, object] | None = None) -> None:
        """Initialise une exception applicative à diagnostic privé.

        Args:
            internal_details: Métadonnées réservées aux logs du service.

        """
        self.message = self.PUBLIC_MESSAGE
        self.internal_details = internal_details or {}
        super().__init__(self.PUBLIC_MESSAGE)

    def to_dict(self) -> dict[str, object]:
        """Convertit l'exception en réponse JSON standardisée.

        Returns:
            Dictionnaire contenant le slug, le message et les détails.
        """
        return {
            "slug": self.SLUG.value,
            "message": self.PUBLIC_MESSAGE,
            "details": {},
        }


class VectorStoreException(ApplicationError):
    """Erreur lors d'une opération ChromaDB."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.VECTOR_STORE_ERROR
    PUBLIC_MESSAGE = "Le stockage vectoriel est temporairement indisponible."


class CollectionException(ApplicationError):
    """Erreur lors de la gestion d'une collection vectorielle."""

    STATUS_CODE = 503
    SLUG = ErrorSlug.COLLECTION_ERROR
    PUBLIC_MESSAGE = "La collection vectorielle n'a pas pu être traitée."


class RetrievalFormatException(ApplicationError):
    """Erreur de format dans les données retournées par le store vectoriel."""

    STATUS_CODE = 502
    SLUG = ErrorSlug.RETRIEVAL_FORMAT_ERROR
    PUBLIC_MESSAGE = "Le stockage vectoriel a retourné une réponse invalide."
