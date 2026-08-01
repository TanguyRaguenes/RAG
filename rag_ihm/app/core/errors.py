from collections.abc import Mapping
from typing import Any

_SAFE_DETAIL_KEYS = frozenset(
    {
        "configuration",
        "contract",
        "dependency",
        "error_type",
        "operation",
        "status_code",
    }
)


class RagApiError(RuntimeError):
    """Erreur IHM contenant un message public et des métadonnées sûres."""

    def __init__(
        self,
        user_message: str,
        details: Mapping[str, Any] | None = None,
        *,
        code: str = "rag_api_error",
        retryable: bool = False,
    ) -> None:
        """Initialise une erreur sans corps backend affichable.

        Args:
            user_message: Message générique destiné à l'utilisateur.
            details: Métadonnées non sensibles, comme un statut HTTP.
            code: Code stable utilisé pour le diagnostic et les tests.
            retryable: Indique si une nouvelle tentative peut réussir sans action.
        """
        self.user_message = user_message
        self.code = code
        self.safe_details = _filter_safe_details(details)
        self.details = self.safe_details
        self.retryable = retryable
        super().__init__(user_message)

    @property
    def status_code(self) -> int | None:
        """Retourne le statut HTTP sûr associé à l'erreur, s'il existe."""
        value = self.safe_details.get("status_code")
        return value if isinstance(value, int) and not isinstance(value, bool) else None


def _filter_safe_details(
    details: Mapping[str, Any] | None,
) -> dict[str, str | int | bool]:
    """Écarte toute métadonnée non explicitement autorisée.

    Args:
        details: Métadonnées candidates produites par une frontière applicative.

    Returns:
        Diagnostic borné sans URL, corps HTTP, token ni contenu utilisateur.
    """
    if not details:
        return {}

    filtered: dict[str, str | int | bool] = {}
    for key, value in details.items():
        if key not in _SAFE_DETAIL_KEYS or not isinstance(value, str | int | bool):
            continue
        filtered[key] = value[:128] if isinstance(value, str) else value
    return filtered
