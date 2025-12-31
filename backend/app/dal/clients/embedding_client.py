import httpx

async def embed_text(text:str, config:dict)-> list[float]:

    base_url = config["embedding"]["url_provider"]
    model=config["embedding"]["model"]

    payload = {"model": model, "input": text}

    text = text.strip()
    if not text:
        raise ValueError("Texte vide")
    
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{base_url}/api/embed", json=payload)
        r.raise_for_status()
        data = r.json()

    return data["embeddings"][0]