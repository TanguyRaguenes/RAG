from typing import Any

import httpx

from app.core.exceptions import LlmApiException


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


async def ask_question_to_api(payload: dict[str, Any], url: str, api_key: str):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        try:
            raise LlmApiException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": f"{str(e)} ; {response.text}"},
                original_exception=None,
            ) from e
        except ValueError:
            raise LlmApiException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
            ) from e
    except httpx.ConnectError as e:
        raise LlmApiException(
            message="Impossible de se connecter à l'API du LLM",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.TimeoutException as e:
        raise LlmApiException(
            message="Timeout lors de l'appel à l'API du LLM",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.RequestError as e:
        # couvre DNS, reset, etc. (hors ConnectError/TimeoutException déjà traités)
        raise LlmApiException(
            message="Erreur réseau lors de l'appel à l'API du LLM",
            details={"url": url, "error": str(e)},
        ) from e
    return data
