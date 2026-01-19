import httpx
from typing import Any

async def judge_client(config:dict,messages: list[dict[str, str]]) -> dict[str, Any]:

    base_url = config["llm"]["url_provider"]
    model = config["llm"]["model"]
    timeout_seconds = config["llm"]["timeout_seconds"]
    temperature = config["llm"]["temperature"]
    stream = config["llm"]["stream"]
    max_tokens = config["llm"]["max_tokens"]
    num_ctx: int = config["llm"]["num_ctx"]


    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        r = await client.post(f"{base_url}/v1/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()

    return {
        "llm_answer": data["choices"][0]["message"]["content"],
    }
