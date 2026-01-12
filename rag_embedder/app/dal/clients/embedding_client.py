import httpx

async def embed_text(text: str, config:dict)-> list[float]:

    url:str = config["embedding"]["url"]
    model=config["embedding"]["model"]
    payload = {"model": model, "input": text}

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()

    return data["embeddings"][0]