import time

import httpx

from config import McpAuthError, McpConfig, load_mcp_config

_token_cache: dict[str, str | int] = {}


async def get_access_token(config: McpConfig | None = None) -> str:
    """Récupère un access token OIDC avec cache mémoire court.

    Args:
        config: Configuration MCP optionnelle. Si absente, elle est chargée depuis l'environnement.

    Returns:
        Access token OIDC à utiliser côté orchestrator.

    Raises:
        McpAuthError: Si l'appel OIDC échoue ou si la réponse ne contient pas d'access token.
        McpConfigError: Si la configuration obligatoire manque.
    """
    config = config or load_mcp_config()
    now = int(time.time())

    if is_cached_token_valid(_token_cache, now):
        return str(_token_cache["access_token"])

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                config.oidc_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": config.oidc_client_id,
                    "client_secret": config.oidc_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()
            token_response = response.json()
    except httpx.HTTPError as exception:
        raise McpAuthError(
            "Impossible d'obtenir un token OIDC",
            details={
                "url": config.oidc_token_url,
                "error_type": type(exception).__name__,
            },
        ) from exception
    except ValueError as exception:
        raise McpAuthError(
            "La réponse OIDC n'est pas un JSON valide",
            details={"url": config.oidc_token_url},
        ) from exception

    try:
        access_token = token_response["access_token"]
    except KeyError as exception:
        raise McpAuthError(
            "La réponse OIDC ne contient pas d'access token",
            details={"url": config.oidc_token_url},
        ) from exception
    expires_in = int(token_response.get("expires_in", 3600))

    cache_access_token(_token_cache, access_token, now + expires_in)

    return access_token


def is_cached_token_valid(cache: dict[str, str | int], now: int) -> bool:
    """Vérifie si le token en cache reste utilisable.

    Args:
        cache: Cache mémoire contenant potentiellement le token et son expiration.
        now: Timestamp courant en secondes.

    Returns:
        `True` si un token est présent et valide au moins 30 secondes.
    """
    return "access_token" in cache and int(cache.get("expires_at", 0)) > now + 30


def cache_access_token(
    cache: dict[str, str | int], access_token: str, expires_at: int
) -> None:
    """Stocke un access token en cache mémoire.

    Args:
        cache: Cache mémoire mutable.
        access_token: Token à stocker sans le logger.
        expires_at: Timestamp d'expiration en secondes.

    Returns:
        Aucune valeur.
    """
    cache["access_token"] = access_token
    cache["expires_at"] = expires_at
