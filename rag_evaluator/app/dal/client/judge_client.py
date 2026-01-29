from typing import Any

import httpx


async def judge_client(config: dict, messages: list[dict[str, str]]) -> dict[str, Any]:
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


async def judge_client_api_openia(
    payload: dict[str, Any], timeout_seconds: int, url: str, api_key: str
):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.is_error:
                print(f"Erreur API ({response.status_code}): {response.text}")

            response.raise_for_status()
            data = response.json()
            return {
                "llm_answer": data["choices"][0]["message"]["content"],
            }

    except httpx.TimeoutException as e:
        print(f"httpx.TimeoutException : {e}")

    except httpx.ConnectError as e:
        print(f"httpx.ConnectError : {e}")

    except httpx.HTTPStatusError as e:
        print(f"httpx.HTTPStatusError : {e}")

    except Exception as e:
        print(f"Exception : {e}")
