import asyncio
import logging
from typing import Any

import jwt
from config import McpConfig
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken

logger = logging.getLogger(__name__)


class PocketIdTokenVerifier:
    """Valide les tokens utilisateur Pocket ID reçus par le transport MCP."""

    def __init__(self, config: McpConfig):
        """Prépare le client JWKS utilisé pour valider les signatures JWT."""
        self.config = config
        self.jwks_client = PyJWKClient(config.oidc_jwks_uri)

    async def verify_token(self, token: str) -> AccessToken | None:
        """Retourne les informations d'accès si le bearer token est valide."""
        try:
            claims = await self._decode_token(token)
        except jwt.PyJWTError as exception:
            logger.warning(
                "Token MCP refusé",
                extra={
                    "service": "rag_mcp",
                    "event": "invalid_incoming_token",
                    "error_type": type(exception).__name__,
                },
            )
            return None

        return AccessToken(
            token=token,
            client_id=_extract_client_id(claims),
            scopes=_extract_scopes(claims),
            expires_at=_extract_expires_at(claims),
            subject=claims.get("sub"),
            claims=claims,
        )

    async def _decode_token(self, token: str) -> dict[str, Any]:
        signing_key = await asyncio.to_thread(
            self.jwks_client.get_signing_key_from_jwt,
            token,
        )

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=self.config.oidc_issuer,
            audience=self.config.oidc_allowed_audiences,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )


def _extract_client_id(claims: dict[str, Any]) -> str:
    """Déduit l'application cliente OIDC à partir des claims standards."""
    client_id = claims.get("client_id") or claims.get("azp")
    if isinstance(client_id, str) and client_id:
        return client_id

    audience = claims.get("aud")
    if isinstance(audience, str):
        return audience
    if isinstance(audience, list) and audience:
        return str(audience[0])

    return "unknown"


def _extract_scopes(claims: dict[str, Any]) -> list[str]:
    """Normalise les scopes OIDC, qu'ils soient exposés en chaîne ou en liste."""
    scope = claims.get("scope") or claims.get("scp") or ""
    if isinstance(scope, str):
        return [item for item in scope.split() if item]
    if isinstance(scope, list):
        return [str(item) for item in scope if item]
    return []


def _extract_expires_at(claims: dict[str, Any]) -> int | None:
    expires_at = claims.get("exp")
    return int(expires_at) if expires_at is not None else None
