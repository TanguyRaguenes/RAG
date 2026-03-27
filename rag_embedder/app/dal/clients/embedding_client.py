import httpx

from app.core.exceptions import EmbeddingServiceException


async def embed_text(text: str, config: dict, is_query: bool) -> list[float]:
    url: str = config["embedding"]["url"]
    model: str = config["embedding"]["model"]
    prefix_query: str = config["embedding"]["prefixes"]["query"]
    prefix_document: str = config["embedding"]["prefixes"]["document"]

    text_to_embed: str

    if is_query:
        text_to_embed = f"{prefix_query}{text}"
    else:
        text_to_embed = f"{prefix_document}{text}"

    payload = {"model": model, "input": text_to_embed}

    payload = {"model": "toto", "input": text_to_embed}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise EmbeddingServiceException(
            message=f"Erreur HTTP {e.response.status_code}",
            details={"url": str(e.request.url), "response": e.response.text},
        ) from e
    except httpx.ConnectError as e:
        raise EmbeddingServiceException(
            message="Impossible de se connecter au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.TimeoutException as e:
        raise EmbeddingServiceException(
            message="Timeout lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.RequestError as e:
        # couvre DNS, reset, etc. (hors ConnectError/TimeoutException déjà traités)
        raise EmbeddingServiceException(
            message="Erreur réseau lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e

    return data["embeddings"][0]
