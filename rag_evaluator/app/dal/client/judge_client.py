from typing import Any

import httpx

from app.core.exceptions import EvaluatorClientError


async def judge_client(config: dict, messages: list[dict[str, str]]) -> dict[str, Any]:
    base_url = config["llm"]["url_provider"]
    timeout_seconds = config["llm"]["timeout_seconds"]
    url = f"{base_url}/v1/chat/completions"
    payload = build_judge_payload(config, messages)

    data = await _post_json(url=url, payload=payload, timeout_seconds=timeout_seconds)

    return format_judge_response(data)


async def judge_client_api_openia(
    payload: dict[str, Any], timeout_seconds: int, url: str, api_key: str | None
) -> dict[str, Any]:
    data = await _post_json(
        url=url,
        payload=payload,
        timeout_seconds=timeout_seconds,
        headers=build_auth_headers(api_key),
    )

    return format_judge_response(data)


def build_judge_payload(config: dict, messages: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "model": config["llm"]["model"],
        "messages": messages,
        "stream": config["llm"]["stream"],
        "options": {
            "temperature": config["llm"]["temperature"],
            "num_ctx": config["llm"]["num_ctx"],
            "num_predict": config["llm"]["max_output_token"],
        },
    }


def build_auth_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def format_judge_response(data: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"llm_answer": data["choices"][0]["message"]["content"]}
    except (KeyError, IndexError, TypeError) as exception:
        raise EvaluatorClientError(
            message="Réponse du juge LLM invalide",
            details={"response": data},
        ) from exception


async def _post_json(
    *,
    url: str,
    payload: dict[str, Any],
    timeout_seconds: int,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exception:
        raise EvaluatorClientError(
            message=f"Erreur HTTP {exception.response.status_code} lors de l'appel au juge LLM",
            details={"url": url, "response": exception.response.text},
        ) from exception
    except httpx.ConnectError as exception:
        raise EvaluatorClientError(
            message="Impossible de se connecter au juge LLM",
            details={"url": url, "error": str(exception)},
        ) from exception
    except httpx.TimeoutException as exception:
        raise EvaluatorClientError(
            message="Timeout lors de l'appel au juge LLM",
            details={"url": url, "error": str(exception)},
        ) from exception
    except httpx.RequestError as exception:
        raise EvaluatorClientError(
            message="Erreur réseau lors de l'appel au juge LLM",
            details={"url": url, "error": str(exception)},
        ) from exception
    except ValueError as exception:
        raise EvaluatorClientError(
            message="Le juge LLM a retourné une réponse JSON invalide",
            details={"url": url},
        ) from exception

    if not isinstance(data, dict):
        raise EvaluatorClientError(
            message="Le juge LLM a retourné un format inattendu",
            details={"url": url, "response": data},
        )

    return data
