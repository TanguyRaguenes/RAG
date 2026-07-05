from typing import Any


class EvaluatorClientError(RuntimeError):
    """Erreur lors d'un appel HTTP sortant depuis le service evaluator."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)
