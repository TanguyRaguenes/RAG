import os
from typing import Any

import httpx

from app.domain.models.vector_store_item_model import VectorStoreItemsBase


async def save_items(vector_store_items: VectorStoreItemsBase) -> Any:
    url = os.getenv("RAG_RETRIEVER_INGEST_DOCUMENTS_URL")

    payload = vector_store_items.model_dump()

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except Exception as e:
            print(e)

    data = resp.json()

    return data
