import os
from typing import Any

import httpx


async def ask_question(question: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=180.0) as client:
        rag_api_url = os.getenv("RAG_API_ASK_QUESTION_URL")
        r = await client.post(rag_api_url, json={"question": question})
        r.raise_for_status()
        return r.json()
