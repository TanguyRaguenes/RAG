import os
from typing import Any
import httpx


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("LLM_BASE_URL", "http://ollama:11434")
        self.model = os.getenv("LLM_MODEL_NAME", "ministral-3:3b")

    async def chat(self, question: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Tu es un assistant utile et concis."},
                {"role": "user", "content": question},
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        # format Ollama: {"message": {"role": "...", "content": "..."}}
        return data["message"]["content"]
