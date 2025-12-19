from typing import Any
import httpx


async def ask_question(question: str, config:dict) -> str:

    base_url = config["llm"]["url_provider"]
    model = config["llm"]["model"]
    timeout_seconds = config["llm"]["timeout_seconds"]
    temperature = config["llm"]["temperature"]
    stream = config["llm"]["stream"]
    max_tokens = config["llm"]["max_tokens"]


    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Tu es un assistant utile et concis."},
            {"role": "user", "content": question},
        ],
        "temperature": temperature,
        "stream": stream,
        "max_tokens":max_tokens
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        r = await client.post(f"{base_url}/v1/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()

    return data["choices"][0]["message"]["content"]
