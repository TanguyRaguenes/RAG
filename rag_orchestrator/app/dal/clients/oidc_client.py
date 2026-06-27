import jwt
from jwt import PyJWKClient
import httpx


class OidcClient:
    def __init__(self, issuer: str, jwks_uri: str, audience: str | list[str] | None = None, userinfo_url: str | None = None):
        self.issuer = issuer
        self.audience = audience
        self.jwks_client = PyJWKClient(jwks_uri)
        self.userinfo_url = userinfo_url

    def validate_token(self, token: str) -> dict:
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
        if not self.userinfo_url:
            return {}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()