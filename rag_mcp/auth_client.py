import time

import httpx

from config import McpConfig, load_mcp_config

_token_cache: dict[str, str | int] = {}


async def get_access_token(config: McpConfig | None = None) -> str:
    config = config or load_mcp_config()
    now = int(time.time())

    if is_cached_token_valid(_token_cache, now):
        return str(_token_cache["access_token"])

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

    access_token = token_response["access_token"]
    expires_in = int(token_response.get("expires_in", 3600))

    cache_access_token(_token_cache, access_token, now + expires_in)

    return access_token


def is_cached_token_valid(cache: dict[str, str | int], now: int) -> bool:
    return "access_token" in cache and int(cache.get("expires_at", 0)) > now + 30


def cache_access_token(
    cache: dict[str, str | int], access_token: str, expires_at: int
) -> None:
    cache["access_token"] = access_token
    cache["expires_at"] = expires_at
