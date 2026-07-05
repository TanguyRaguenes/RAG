import json
from typing import Any

import httpx

from config import McpConfig


async def retrieve_documentation_chunks(
    *,
    config: McpConfig,
    question: str,
    access_token: str,
) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            config.rag_orchestrator_url,
            json={"question": question},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response.raise_for_status()

        return format_retrieved_chunks_response(response.json())


def format_retrieved_chunks_response(data: dict[str, Any]) -> str:
    retrieved_chunks = data.get("retrieved_chunks", [])

    if not retrieved_chunks:
        return "Aucune information trouvée."

    return json.dumps(retrieved_chunks, ensure_ascii=False, indent=2)
