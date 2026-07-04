import os
from functools import lru_cache

import asyncpg
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dal.clients.oidc_client import OidcClient
from app.services.auth_service import AuthService

def get_config(request: Request) -> dict:
    return request.app.state.config


def get_db_pool(request: Request) -> asyncpg.Pool:
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

    allowed_audiences = os.environ["OIDC_ALLOWED_AUDIENCES"].split(",")
    
    oidc_client = OidcClient(
        issuer=os.environ["OIDC_ISSUER"],
        jwks_uri=os.environ["OIDC_JWKS_URI"],
        audience=allowed_audiences,
        userinfo_url=os.environ.get("OIDC_USERINFO_URL")
    )

    return AuthService(oidc_client)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        return await auth_service.authenticate(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
