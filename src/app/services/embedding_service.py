import httpx
import aiofiles

from pathlib import Path


async def read_markdown_files(path: Path)->list[dict]:
    pages = []
    root = Path(path).resolve()

    for path in root.rglob("*.md"):

        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            content = await f.read()

        pages.append({
            "page_path": path.relative_to(root).as_posix(),
            "content": content
        })
    
    return pages

    


async def embed_text(text:str, config:dict)-> list[float]:

    base_url = config["embedding"]["url_provider"]
    model=config["embedding"]["model"]

    payload = {"model": model, "prompt": text}

    text = text.strip()
    if not text:
        return
    
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{base_url}/api/embeddings", json=payload)
        r.raise_for_status()
        data = r.json()

    return data["embedding"]