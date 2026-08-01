from enum import Enum
from typing import Any

QUOTA_EXCEEDED_PUBLIC_MESSAGE = (
    "Vous avez consommé votre enveloppe de tokens. "
    "Veuillez vous rapprocher de votre administrateur."
)


class ErrorSlug(str, Enum):
    """Codes stables associés aux erreurs publiques de l'orchestrator."""

    INTERNAL = "ERR_INTERNAL"
    USAGE_SESSION_INVALID = "ERR_USAGE_SESSION_INVALID"
    QUESTION_QUOTA_EXCEEDED = "ERR_QUESTION_QUOTA_EXCEEDED"
    QUOTA_EXCEEDED = "ERR_QUOTA_EXCEEDED"
    QUOTA_INACTIVE = "ERR_QUOTA_INACTIVE"
    INVALID_REQUEST = "ERR_INVALID_REQUEST"
    RESOURCE_NOT_FOUND = "ERR_RESOURCE_NOT_FOUND"
    AUTHENTICATION_REQUIRED = "ERR_AUTHENTICATION_REQUIRED"
    AUTHENTICATION_INVALID = "ERR_AUTHENTICATION_INVALID"
    FORBIDDEN = "ERR_FORBIDDEN"
    DATABASE = "ERR_DATABASE"
    IDENTITY_PROVIDER = "ERR_IDENTITY_PROVIDER"
    DEPENDENCY_RESPONSE = "ERR_DEPENDENCY_RESPONSE"
    EMBEDDING_CONTAINER_ERROR = "ERR_EMBEDDING_SERVICE"
    RETRIEVER_CONTAINER_ERROR = "ERR_RETRIEVER_SERVICE"
    RERANKER_CONTAINER_ERROR = "ERR_RERANKER_SERVICE"
    LLM_API_ERROR = "ERR_LLM_API"


class ApplicationError(Exception):
    """Base des erreurs contrôlées converties par le handler FastAPI central."""

    STATUS_CODE = 500
    SLUG = ErrorSlug.INTERNAL
    PUBLIC_MESSAGE = "Une erreur interne est survenue."

    def __init__(
        self,
        internal_message: str | None = None,
        details: dict[str, Any] | None = None,
        original_exception: dict[str, Any] | None = None,
        *,
        public_details: dict[str, Any] | None = None,
    ) -> None:
        """Conserve le diagnostic interne séparément du contrat public.

        Args:
            internal_message: Diagnostic technique stable, jamais sérialisé ni journalisé.
            details: Contexte interne non sensible, conservé pour le diagnostic local.
            original_exception: Ancien contexte amont conservé hors du payload public.
            public_details: Détails explicitement déclarés sûrs pour le client API.
        """
        self.internal_message = internal_message or type(self).__name__
        self.details = details or {}
        self.original_exception = original_exception
        self.public_details = public_details or {}
        super().__init__(self.internal_message)

    def to_dict(self) -> dict[str, Any]:
        """Construit le contrat d'erreur public stable.

        Returns:
            Payload contenant uniquement slug, message public et détails sûrs.
        """
        return {
            "slug": self.SLUG.value,
            "message": self.PUBLIC_MESSAGE,
            "details": self.public_details,
        }

    def to_public_dict(self) -> dict[str, Any]:
        """Conserve le nom historique de la sérialisation publique.

        Returns:
            Même payload public que :meth:`to_dict`.
        """
        return self.to_dict()


# Nom historique conservé pour les imports des clients interservices existants.
OrchestratorContainerCustomException = ApplicationError


class ClientApplicationError(ApplicationError):
    """Base des erreurs attendues causées par une requête cliente."""

    STATUS_CODE = 400


class UsageSessionValidationError(ClientApplicationError):
    """Signale qu'une session d'usage ne peut pas être créée."""

    SLUG = ErrorSlug.USAGE_SESSION_INVALID
    PUBLIC_MESSAGE = "La session d'usage demandée n'est pas valide."


class QuotaError(ClientApplicationError):
    """Base des refus liés au quota d'un utilisateur."""

    STATUS_CODE = 429
    PUBLIC_MESSAGE = QUOTA_EXCEEDED_PUBLIC_MESSAGE


class QuestionQuotaExceededError(QuotaError):
    """Signale que le quota interdit l'exécution d'une question."""

    SLUG = ErrorSlug.QUESTION_QUOTA_EXCEEDED


class QuotaExceededError(QuotaError):
    """Signale que la consommation mensuelle a atteint le plafond actif."""

    SLUG = ErrorSlug.QUOTA_EXCEEDED

    def __init__(self, max_tokens: int, consumed_tokens: int) -> None:
        """Conserve les compteurs de quota sans les exposer au client.

        Args:
            max_tokens: Plafond mensuel configuré pour l'utilisateur.
            consumed_tokens: Consommation déjà comptabilisée sur la période.
        """
        self.max_tokens = max_tokens
        self.consumed_tokens = consumed_tokens
        super().__init__(
            "User token quota exceeded",
            details={"max_tokens": max_tokens, "consumed_tokens": consumed_tokens},
        )


class QuotaInactiveError(QuotaError):
    """Signale que le quota utilisateur est désactivé."""

    SLUG = ErrorSlug.QUOTA_INACTIVE


class InvalidRequestError(ClientApplicationError):
    """Signale une règle métier invalide dans une requête pourtant bien formée."""

    SLUG = ErrorSlug.INVALID_REQUEST
    PUBLIC_MESSAGE = "La requête ne respecte pas les règles attendues."


class ResourceNotFoundError(ClientApplicationError):
    """Signale qu'une ressource métier demandée n'existe pas."""

    STATUS_CODE = 404
    SLUG = ErrorSlug.RESOURCE_NOT_FOUND
    PUBLIC_MESSAGE = "La ressource demandée est introuvable."


class AuthenticationRequiredError(ClientApplicationError):
    """Signale l'absence de credentials bearer."""

    STATUS_CODE = 401
    SLUG = ErrorSlug.AUTHENTICATION_REQUIRED
    PUBLIC_MESSAGE = "Une authentification bearer est requise."


class AuthenticationInvalidError(ClientApplicationError):
    """Signale que les credentials bearer ne peuvent pas être validés."""

    STATUS_CODE = 401
    SLUG = ErrorSlug.AUTHENTICATION_INVALID
    PUBLIC_MESSAGE = "Le token d'authentification n'est pas valide."


class ForbiddenError(ClientApplicationError):
    """Signale que l'identité courante ne possède pas le rôle requis."""

    STATUS_CODE = 403
    SLUG = ErrorSlug.FORBIDDEN
    PUBLIC_MESSAGE = "Vous n'êtes pas autorisé à accéder à cette ressource."


class InfrastructureError(ApplicationError):
    """Base des indisponibilités techniques contrôlées."""

    STATUS_CODE = 503


class DatabaseError(InfrastructureError):
    """Traduit une erreur PostgreSQL à la frontière repository."""

    SLUG = ErrorSlug.DATABASE
    PUBLIC_MESSAGE = "Le service de données est temporairement indisponible."


class IdentityProviderError(InfrastructureError):
    """Traduit une erreur HTTP ou de réponse du fournisseur d'identité."""

    SLUG = ErrorSlug.IDENTITY_PROVIDER
    PUBLIC_MESSAGE = "Le fournisseur d'identité est temporairement indisponible."


class DependencyResponseError(InfrastructureError):
    """Signale une réponse décodable mais incompatible avec le contrat attendu."""

    STATUS_CODE = 502
    SLUG = ErrorSlug.DEPENDENCY_RESPONSE
    PUBLIC_MESSAGE = "Une dépendance a retourné une réponse invalide."


class EmbedderContainerException(InfrastructureError):
    """Erreur lors de l'interaction avec le conteneur embedder."""

    SLUG = ErrorSlug.EMBEDDING_CONTAINER_ERROR
    PUBLIC_MESSAGE = "Le service d'embedding est temporairement indisponible."


class RetrieverContainerException(InfrastructureError):
    """Erreur lors de l'interaction avec le conteneur retriever."""

    SLUG = ErrorSlug.RETRIEVER_CONTAINER_ERROR
    PUBLIC_MESSAGE = "Le service de recherche est temporairement indisponible."


class RerankerContainerException(InfrastructureError):
    """Erreur lors de l'interaction avec le conteneur reranker."""

    SLUG = ErrorSlug.RERANKER_CONTAINER_ERROR
    PUBLIC_MESSAGE = "Le service de classement est temporairement indisponible."


class LlmApiException(InfrastructureError):
    """Erreur lors de l'interaction avec une API de génération."""

    SLUG = ErrorSlug.LLM_API_ERROR
    PUBLIC_MESSAGE = "Le service de génération est temporairement indisponible."
