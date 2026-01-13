import httpx


async def embed_text(text: str, config: dict, isQuery: bool) -> list[float]:
    url: str = config["embedding"]["url"]
    model: str = config["embedding"]["model"]
    prefix_query: str = config["embedding"]["prefixes"]["query"]
    prefix_document: str = config["embedding"]["prefixes"]["document"]

    text_to_embed: str

    if isQuery:
        text_to_embed = f"{prefix_query}{text}"
    else:
        text_to_embed = f"{prefix_document}{text}"

    payload = {"model": model, "input": text_to_embed}

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()

    return data["embeddings"][0]
