import os
from typing import Any
import httpx

async def rag_api_client(question: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        rag_api_url = os.getenv("RAG_API_URL")
        r = await client.post(rag_api_url, json={"question": question})
        r.raise_for_status()
        return r.json()