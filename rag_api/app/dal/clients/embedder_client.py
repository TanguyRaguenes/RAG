import os
from typing import Any

import httpx


async def embed_question(question: str) -> Any:
    url = os.getenv("RAG_EMBEDDER_EMBED_QUESTION_URL")

    payload = {"text": question}

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except Exception as e:
            print(e)

    data = resp.json()

    return data["embeded_text"]
