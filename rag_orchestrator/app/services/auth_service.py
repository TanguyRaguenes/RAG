import logging

import httpx

from app.dal.clients.oidc_client import OidcClient
from app.schemas.authenticated_user_schema import AuthenticatedUser

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, oidc_client: OidcClient):
        """Conserve le client OIDC utilisé par le service d'authentification.

        Args:
            oidc_client: Client OIDC utilisé pour valider les tokens et charger le profil utilisateur.
        """
        self.oidc_client = oidc_client

    async def authenticate(self, token: str) -> AuthenticatedUser:
        """Authentifie un utilisateur à partir du token transmis par le client HTTP.

        Args:
            token: Token OIDC ou JWT à valider sans l'écrire dans les logs.

        Returns:
            Profil authentifié construit depuis les claims JWT et userinfo.
        """
        claims = self.oidc_client.validate_token(token)
        _log_user_claims("validated_token", claims)

        is_machine_token = claims.get("sub", "").startswith("client-")

        if not is_machine_token:
            try:
                userinfo = await self.oidc_client.get_userinfo(token)
                _log_user_claims("userinfo_response", userinfo)
                claims = {**claims, **userinfo}
            except httpx.HTTPStatusError as exception:
                logger.info(
                    "Userinfo Pocket ID refusé pour le token utilisateur",
                    extra={
                        "service": "rag_orchestrator",
                        "event": "userinfo_rejected",
                        "status_code": exception.response.status_code,
                    },
                )
                try:
                    pocket_id_user = await self.oidc_client.get_user_by_id(claims["sub"])
                except httpx.HTTPError as api_exception:
                    logger.warning(
                        "Enrichissement utilisateur Pocket ID indisponible",
                        extra={
                            "service": "rag_orchestrator",
                            "event": "pocket_id_user_lookup_failed",
                            "error_type": type(api_exception).__name__,
                        },
                    )
                else:
                    if pocket_id_user:
                        _log_user_claims("pocket_id_api_user", pocket_id_user)
                        claims = {**claims, **pocket_id_user}

        return AuthenticatedUser(
            issuer=claims["iss"],
            sub=claims["sub"],
            email=claims.get("email"),
            name=claims.get("name"),
            display_name=claims.get("display_name") or claims.get("name"),
            preferred_username=claims.get("preferred_username"),
            groups=claims.get("groups", []),
        )


def _log_user_claims(event: str, claims: dict) -> None:
    """Journalise uniquement la présence des claims utiles, jamais le token brut.

    Args:
        event: Étape d'authentification observée.
        claims: Claims JWT ou userinfo à résumer sans exposer les valeurs sensibles.
    """
    logger.debug(
        "Claims utilisateur OAuth reçus",
        extra={
            "service": "rag_orchestrator",
            "event": event,
            "issuer": claims.get("iss"),
            "subject_present": bool(claims.get("sub")),
            "email_present": bool(claims.get("email")),
            "display_name_present": bool(claims.get("display_name") or claims.get("name")),
            "preferred_username_present": bool(claims.get("preferred_username")),
            "audience": claims.get("aud"),
            "scope": claims.get("scope") or claims.get("scp"),
        },
    )
