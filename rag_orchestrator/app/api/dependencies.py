import os
from functools import lru_cache

import asyncpg
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dal.clients.oidc_client import OidcClient
from app.services.auth_service import AuthService


def get_config(request: Request) -> dict:
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


# Déclare un mécanisme d'authentification HTTP Bearer.
# Il va lire automatiquement le header :
# Authorization: Bearer <token>
# auto_error=False signifie :
# - si le header est absent, FastAPI ne déclenche pas l'erreur tout seul ;
# - on gère nous-mêmes l'erreur dans get_current_user.
security = HTTPBearer(auto_error=False)


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
    )

    return AuthService(oidc_client)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Valide le bearer token courant et retourne l'utilisateur authentifié.

    Args:
        credentials: Credentials bearer extraits de l'en-tête Authorization.
        auth_service: Service chargé de valider le token bearer reçu par l'API.

    Returns:
        Utilisateur authentifié ou erreur HTTP si le token est invalide.

    Raises:
        HTTPException: Si la requête ne respecte pas les règles d'authentification, d'autorisation ou de validation.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Il manque le bearer token",
        )

    try:
        return await auth_service.authenticate(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Le token d'authentification n'est pas valide.",
        )
