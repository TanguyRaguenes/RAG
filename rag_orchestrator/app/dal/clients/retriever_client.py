import os
from typing import Any

import httpx


async def retrieve_chunks(embeded_question: list[float]) -> Any:
    url = os.getenv("RAG_RETRIEVER_RETRIEVE_CHUNKS_URL")

    payload = {"embeded_question": embeded_question}

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except Exception as e:
            print(e)

    data = resp.json()

    return data["chunks"]
