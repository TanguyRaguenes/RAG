import logging
from typing import Any, Protocol

import jwt

from app.core.exceptions import IdentityProviderError
from app.schemas.authenticated_user_schema import AuthenticatedUser

logger = logging.getLogger(__name__)

PROFILE_CLAIMS = frozenset(
    {"email", "name", "display_name", "preferred_username", "groups"}
)


class OidcClientProtocol(Protocol):
    """Contrat du client OIDC requis par le service d'authentification."""

    def validate_token(self, token: str) -> dict[str, Any]:
        """Valide un token signé et retourne ses claims de confiance.

        Args:
            token: Bearer token reçu par l'API, jamais journalisé.

        Returns:
            Claims dont la signature, l'émetteur et l'audience sont validés.
        """
        ...

    async def get_userinfo(self, access_token: str) -> dict[str, Any]:
        """Charge le profil OIDC associé au token utilisateur.

        Args:
            access_token: Token validé transmis au endpoint userinfo.

        Returns:
            Claims de profil fournis par le serveur OIDC.
        """
        ...

    async def get_user_by_id(self, user_id: str) -> dict[str, Any]:
        """Charge un profil Pocket ID depuis son sujet validé.

        Args:
            user_id: Claim `sub` validé utilisé comme identifiant Pocket ID.

        Returns:
            Claims d'affichage récupérés via l'API serveur Pocket ID.
        """
        ...


class AuthService:
    def __init__(self, oidc_client: OidcClientProtocol) -> None:
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

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise jwt.InvalidTokenError("token subject is required")

        is_machine_token = subject.startswith("client-")

        if not is_machine_token:
            try:
                userinfo = await self.oidc_client.get_userinfo(token)
                _log_user_claims("userinfo_response", userinfo)
                if userinfo:
                    claims = _merge_userinfo_claims(claims, userinfo)
            except IdentityProviderError:
                logger.info(
                    "Userinfo Pocket ID indisponible pour le token utilisateur",
                    extra={
                        "service": "rag_orchestrator",
                        "event": "userinfo_unavailable",
                        "error_type": "IdentityProviderError",
                    },
                )
                try:
                    pocket_id_user = await self.oidc_client.get_user_by_id(subject)
                except IdentityProviderError:
                    logger.warning(
                        "Enrichissement utilisateur Pocket ID indisponible",
                        extra={
                            "service": "rag_orchestrator",
                            "event": "pocket_id_user_lookup_failed",
                            "error_type": "IdentityProviderError",
                        },
                    )
                else:
                    if pocket_id_user:
                        _log_user_claims("pocket_id_api_user", pocket_id_user)
                        claims = _merge_profile_claims(claims, pocket_id_user)

        issuer = claims.get("iss")
        if not isinstance(issuer, str) or not issuer:
            raise jwt.InvalidTokenError("token issuer is required")

        return AuthenticatedUser(
            issuer=issuer,
            sub=subject,
            email=claims.get("email"),
            name=claims.get("name"),
            display_name=claims.get("display_name") or claims.get("name"),
            preferred_username=claims.get("preferred_username"),
            groups=claims.get("groups", []),
        )


def _merge_userinfo_claims(
    validated_claims: dict[str, Any],
    userinfo: dict[str, Any],
) -> dict[str, Any]:
    """Enrichit les claims validés après contrôle strict du sujet userinfo.

    Args:
        validated_claims: Claims issus du JWT dont `iss/sub` font autorité.
        userinfo: Profil retourné par l'endpoint OIDC userinfo.

    Returns:
        Claims enrichis uniquement avec les attributs de profil autorisés.

    Raises:
        jwt.InvalidTokenError: Si le profil ne porte pas exactement le même `sub`.
    """
    if userinfo.get("sub") != validated_claims.get("sub"):
        raise jwt.InvalidTokenError("userinfo subject does not match token subject")
    return _merge_profile_claims(validated_claims, userinfo)


def _merge_profile_claims(
    validated_claims: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Fusionne seulement les claims d'affichage sans modifier l'identité validée.

    Args:
        validated_claims: Claims JWT validés qui restent la source d'identité.
        profile: Profil externe potentiellement enrichi par Pocket ID.

    Returns:
        Copie des claims validés enrichie des champs de profil autorisés.
    """
    profile_claims = {key: profile[key] for key in PROFILE_CLAIMS if key in profile}
    return {**validated_claims, **profile_claims}


def _log_user_claims(event: str, claims: dict[str, Any]) -> None:
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
            "issuer_present": bool(claims.get("iss")),
            "subject_present": bool(claims.get("sub")),
            "email_present": bool(claims.get("email")),
            "display_name_present": bool(
                claims.get("display_name") or claims.get("name")
            ),
            "preferred_username_present": bool(claims.get("preferred_username")),
            "audience_present": bool(claims.get("aud")),
            "scope_present": bool(claims.get("scope") or claims.get("scp")),
        },
    )
