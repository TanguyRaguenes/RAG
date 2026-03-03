from typing import Any

import httpx


async def ask_question_to_llm(payload: dict[str, Any], timeout_seconds, url):
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload)
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


async def ask_question_to_api_openai(
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
            return data

    except httpx.TimeoutException as e:
        print(f"httpx.TimeoutException : {e}")

    except httpx.ConnectError as e:
        print(f"httpx.ConnectError : {e}")

    except httpx.HTTPStatusError as e:
        print(f"httpx.HTTPStatusError : {e}")

    except Exception as e:
        print(f"Exception : {e}")
