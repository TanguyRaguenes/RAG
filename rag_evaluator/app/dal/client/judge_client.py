import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.exceptions import EvaluatorClientError
from app.core.metrics import (
    evaluator_external_call_duration_seconds,
    evaluator_errors_total,
)

tracer = trace.get_tracer(__name__)


async def judge_client(config: dict, messages: list[dict[str, str]]) -> dict[str, Any]:
    """Appelle le juge LLM local pour évaluer une réponse RAG.

    Args:
        config: Configuration du LLM juge local.
        messages: Messages du prompt d'évaluation.

    Returns:
        Réponse formatée contenant `llm_answer`.

    Raises:
        EvaluatorClientError: Si l'appel ou le format de réponse du juge est invalide.
        KeyError: Si la configuration LLM attendue est absente.
    """
    base_url = config["llm"]["url_provider"]
    timeout_seconds = config["llm"]["timeout_seconds"]
    url = f"{base_url}/v1/chat/completions"
    payload = build_judge_payload(config, messages)

    data = await _post_json(url=url, payload=payload, timeout_seconds=timeout_seconds)

    return format_judge_response(data)


async def judge_client_api_openia(
    payload: dict[str, Any], timeout_seconds: int, url: str, api_key: str | None
) -> dict[str, Any]:
    """Appelle le juge LLM via une API externe.

    Args:
        payload: Corps JSON envoyé à l'API LLM.
        timeout_seconds: Timeout HTTP de l'appel.
        url: Endpoint HTTP de l'API LLM.
        api_key: Clé API optionnelle, jamais loggée.

    Returns:
        Réponse formatée contenant `llm_answer`.

    Raises:
        EvaluatorClientError: Si l'appel ou le format de réponse du juge est invalide.
    """
    data = await _post_json(
        url=url,
        payload=payload,
        timeout_seconds=timeout_seconds,
        headers=build_auth_headers(api_key),
    )

    return format_judge_response(data)


def build_judge_payload(config: dict, messages: list[dict[str, str]]) -> dict[str, Any]:
    """Construit le payload du juge LLM local.

    Args:
        config: Configuration du LLM juge local.
        messages: Messages du prompt d'évaluation.

    Returns:
        Payload JSON compatible avec le juge local.

    Raises:
        KeyError: Si la configuration LLM attendue est absente.
    """
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
    """Construit les headers HTTP du juge API.

    Args:
        api_key: Clé API optionnelle.

    Returns:
        Headers HTTP sans logger la clé.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def format_judge_response(data: dict[str, Any]) -> dict[str, Any]:
    """Normalise la réponse du juge LLM.

    Args:
        data: Réponse JSON brute du juge.

    Returns:
        Dictionnaire contenant `llm_answer`.

    Raises:
        EvaluatorClientError: Si la réponse ne contient pas le contenu attendu.
    """
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
    """Envoie une requête JSON HTTP au juge LLM.

    Args:
        url: Endpoint HTTP cible.
        payload: Corps JSON envoyé.
        timeout_seconds: Timeout HTTP de l'appel.
        headers: Headers HTTP optionnels.

    Returns:
        Réponse JSON décodée.

    Raises:
        EvaluatorClientError: Si l'appel HTTP échoue ou si la réponse est invalide.
    """
    start = time.perf_counter()
    try:
        with tracer.start_as_current_span("evaluator.call_judge"):
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
    except httpx.HTTPStatusError as exception:
        _record_external_error("judge", "judge", "http_status", start)
        raise EvaluatorClientError(
            message=f"Erreur HTTP {exception.response.status_code} lors de l'appel au juge LLM",
            details={"url": url, "response": exception.response.text},
        ) from exception
    except httpx.ConnectError as exception:
        _record_external_error("judge", "judge", "connect_error", start)
        raise EvaluatorClientError(
            message="Impossible de se connecter au juge LLM",
            details={"url": url, "error": str(exception)},
        ) from exception
    except httpx.TimeoutException as exception:
        _record_external_error("judge", "judge", "timeout", start)
        raise EvaluatorClientError(
            message="Timeout lors de l'appel au juge LLM",
            details={"url": url, "error": str(exception)},
        ) from exception
    except httpx.RequestError as exception:
        _record_external_error("judge", "judge", "request_error", start)
        raise EvaluatorClientError(
            message="Erreur réseau lors de l'appel au juge LLM",
            details={"url": url, "error": str(exception)},
        ) from exception
    except ValueError as exception:
        _record_external_error("judge", "judge", "invalid_json", start)
        raise EvaluatorClientError(
            message="Le juge LLM a retourné une réponse JSON invalide",
            details={"url": url},
        ) from exception

    if not isinstance(data, dict):
        _record_external_error("judge", "judge", "invalid_format", start)
        raise EvaluatorClientError(
            message="Le juge LLM a retourné un format inattendu",
            details={"url": url, "response": data},
        )

    evaluator_external_call_duration_seconds.labels(
        dependency="judge", operation="judge", status="success"
    ).observe(time.perf_counter() - start)
    return data


def _record_external_error(
    dependency: str, operation: str, error_type: str, start: float
) -> None:
    """Enregistre une erreur d'appel externe evaluator.

    Args:
        dependency: Nom stable de la dépendance appelée.
        operation: Nom stable de l'opération appelée.
        error_type: Type d'erreur à faible cardinalité.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    evaluator_errors_total.labels(operation=operation, error_type=error_type).inc()
    evaluator_external_call_duration_seconds.labels(
        dependency=dependency, operation=operation, status="error"
    ).observe(time.perf_counter() - start)
