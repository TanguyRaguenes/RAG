from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import EvaluatorConfig
from app.core.exceptions import EvaluatorAuthenticationError

_bearer_scheme = HTTPBearer(auto_error=False)
BearerCredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(_bearer_scheme),
]


def get_config(request: Request) -> EvaluatorConfig:
    """Retourne la configuration chargée au démarrage de l'application FastAPI.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Configuration applicative disponible dans `app.state`.
    """
    return request.app.state.config


def get_bearer_token(credentials: BearerCredentialsDep) -> str:
    """Extrait le bearer requis sans le journaliser ni le stocker globalement.

    Args:
        credentials: Credentials analysés par le schéma de sécurité HTTP Bearer.

    Returns:
        Token opaque transmis uniquement aux clients de l'orchestrator.

    Raises:
        EvaluatorAuthenticationError: Si le header est absent ou mal formé.
    """
    if (
        credentials is None
        or credentials.scheme.casefold() != "bearer"
        or not credentials.credentials.strip()
    ):
        raise EvaluatorAuthenticationError(message="Authentification bearer requise")
    return credentials.credentials
