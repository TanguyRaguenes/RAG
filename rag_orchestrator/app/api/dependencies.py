import os
from functools import lru_cache
from typing import Any

import asyncpg
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationInvalidError, AuthenticationRequiredError
from app.dal.clients.oidc_client import OidcClient
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.services.auth_service import AuthService
from app.services.question_orchestration_service import QuestionOrchestrationService


def get_config(request: Request) -> dict[str, Any]:
    """Retourne la configuration chargée au démarrage de l'application FastAPI.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Configuration applicative disponible dans `app.state`.
    """
    return request.app.state.config


def get_db_pool(request: Request) -> asyncpg.Pool:
    """Retourne le pool PostgreSQL partagé par les routes de suivi d'usage.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Pool PostgreSQL partagé par l'application.
    """
    return request.app.state.db_pool


config_dependency = Depends(get_config)
db_pool_dependency = Depends(get_db_pool)


def get_question_orchestration_service(
    config: dict[str, Any] = config_dependency,
    db_pool: asyncpg.Pool = db_pool_dependency,
) -> QuestionOrchestrationService:
    """Construit le service de question avec les ressources de la requête courante.

    Args:
        config: Configuration applicative partagée par le pipeline RAG.
        db_pool: Pool PostgreSQL partagé par le suivi d'usage.

    Returns:
        Service d'orchestration prêt à traiter les routes de question et retrieval.
    """
    return QuestionOrchestrationService(config, db_pool)


# Déclare un mécanisme d'authentification HTTP Bearer.
# Il va lire automatiquement le header :
# Authorization: Bearer <token>
# auto_error=False signifie :
# - si le header est absent, FastAPI ne déclenche pas l'erreur tout seul ;
# - on gère nous-mêmes l'erreur dans get_current_user.
security = HTTPBearer(auto_error=False)
security_dependency = Depends(security)


@lru_cache
def get_auth_service() -> AuthService:
    """Construit le service d'authentification OIDC à partir de la configuration courante.

    Returns:
        Données auth service récupérées depuis la source du service.
    """
    allowed_audiences = os.environ["OIDC_ALLOWED_AUDIENCES"].split(",")

    oidc_client = OidcClient(
        issuer=os.environ["OIDC_ISSUER"],
        jwks_uri=os.environ["OIDC_JWKS_URI"],
        audience=allowed_audiences,
        userinfo_url=os.environ.get("OIDC_USERINFO_URL"),
        pocket_id_api_url=os.environ.get("POCKET_ID_API_URL"),
        pocket_id_api_key=os.environ.get("POCKET_ID_API_KEY"),
    )

    return AuthService(oidc_client)


auth_service_dependency = Depends(get_auth_service)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = security_dependency,
    auth_service: AuthService = auth_service_dependency,
) -> AuthenticatedUser:
    """Valide le bearer token courant et retourne l'utilisateur authentifié.

    Args:
        credentials: Credentials bearer extraits de l'en-tête Authorization.
        auth_service: Service chargé de valider le token bearer reçu par l'API.

    Returns:
        Utilisateur authentifié construit depuis le bearer token.

    Raises:
        AuthenticationRequiredError: Si aucun bearer token n'est fourni.
        AuthenticationInvalidError: Si la validation du token échoue.
    """
    if credentials is None:
        raise AuthenticationRequiredError("Bearer credentials are missing")

    try:
        return await auth_service.authenticate(credentials.credentials)
    except jwt.PyJWTError as exception:
        raise AuthenticationInvalidError(
            "Bearer token validation failed"
        ) from exception
