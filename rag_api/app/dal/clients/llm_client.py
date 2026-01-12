import httpx
from typing import Any

async def ask_question_to_llm(payload:dict[str, Any], timeout_seconds,base_url):

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(f"{base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

        return data
    except httpx.TimeoutException as e:
        print(f"httpx.TimeoutException : {e}")

    except httpx.ConnectError as e:
        print(f"httpx.ConnectError : {e}")

    except httpx.HTTPStatusError as e:
        print(f"httpx.HTTPStatusError : {e}")

    except Exception as e:
        print(f"Exception : {e}")