from app.dal.clients.oidc_client import OidcClient
from app.schemas.authenticated_user_schema import AuthenticatedUser


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

        is_machine_token = claims.get("sub", "").startswith("client-")

        if not is_machine_token:
            userinfo = await self.oidc_client.get_userinfo(token)
            claims = {**claims, **userinfo}

        return AuthenticatedUser(
            sub=claims["sub"],
            email=claims.get("email"),
            name=claims.get("name"),
            preferred_username=claims.get("preferred_username"),
            groups=claims.get("groups", []),
        )
