import jwt
from jwt import PyJWKClient
import httpx


class OidcClient:
    def __init__(
        self,
        issuer: str,
        jwks_uri: str,
        audience: str | list[str] | None = None,
        userinfo_url: str | None = None,
        pocket_id_api_url: str | None = None,
        pocket_id_api_key: str | None = None,
    ):
        """Configure le client OIDC utilisé pour valider les JWT et charger le profil.

        Args:
            issuer: URL de l'émetteur OIDC utilisé pour valider les tokens.
            jwks_uri: Endpoint JWKS contenant les clés publiques de validation JWT.
            audience: Audience JWT attendue pour accepter un access token OIDC.
            userinfo_url: Endpoint OIDC utilisé pour récupérer les informations de profil.
            pocket_id_api_url: URL de l'API REST Pocket ID utilisée pour enrichir un profil.
            pocket_id_api_key: Clé API serveur Pocket ID, jamais exposée dans les logs.
        """
        self.issuer = issuer
        self.audience = audience
        self.jwks_client = PyJWKClient(jwks_uri)
        self.userinfo_url = userinfo_url
        self.pocket_id_api_url = pocket_id_api_url.rstrip("/") if pocket_id_api_url else None
        self.pocket_id_api_key = pocket_id_api_key

    def validate_token(self, token: str) -> dict:
        """Valide un JWT OIDC et retourne ses claims.

        Args:
            token: Token OIDC ou JWT à valider sans l'écrire dans les logs.

        Returns:
            Claims du JWT validés avec signature, expiration, issuer et audience attendus.
        """
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)

        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": bool(self.audience),
        }

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience if self.audience else None,
            options=options,
        )

    async def get_userinfo(self, access_token: str) -> dict:
        """Récupère les informations utilisateur auprès de l'endpoint OIDC userinfo.

        Args:
            access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.

        Returns:
            Claims utilisateur retournés par l'endpoint OIDC userinfo.
        """
        if not self.userinfo_url:
            return {}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_user_by_id(self, user_id: str) -> dict:
        """Récupère un utilisateur Pocket ID depuis l'API serveur par son identifiant.

        Args:
            user_id: Identifiant Pocket ID correspondant au claim `sub`.

        Returns:
            Claims utilisateur compatibles avec le reste du service d'authentification.
        """
        if not self.pocket_id_api_url or not self.pocket_id_api_key:
            return {}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self.pocket_id_api_url}/users/{user_id}",
                headers={"X-API-Key": self.pocket_id_api_key},
            )
            response.raise_for_status()
            user = response.json()

        return _pocket_id_user_to_claims(user)


def _pocket_id_user_to_claims(user: dict) -> dict:
    """Convertit le DTO utilisateur Pocket ID en claims internes.

    Args:
        user: Réponse JSON de l'API REST Pocket ID `/api/users/{id}`.

    Returns:
        Claims `email`, `display_name`, `name` et `preferred_username` si disponibles.
    """
    display_name = user.get("displayName")
    first_name = user.get("firstName")
    last_name = user.get("lastName")
    name_parts = [part for part in [first_name, last_name] if part]
    name = display_name or " ".join(name_parts) or None

    return {
        "email": user.get("email"),
        "display_name": display_name or name,
        "name": name,
        "preferred_username": user.get("username"),
    }
