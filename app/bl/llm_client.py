import os
from typing import Any
import httpx


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("LLM_BASE_URL", "http://ollama:11434")
        #self.model = os.getenv("LLM_MODEL_NAME", "ministral-3:3b")
        self.model = os.getenv("LLM_MODEL_NAME", "gemma3:270m")
        
    async def chat(self, question: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Tu es un assistant utile et concis."},
                {"role": "user", "content": question},
            ],
            "temperature": 0.2,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()

        return data["choices"][0]["message"]["content"]
