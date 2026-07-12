import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.exceptions import LlmApiException
from app.core.metrics import (
    orchestrator_external_call_duration_seconds,
    orchestrator_external_call_errors_total,
)

tracer = trace.get_tracer(__name__)


async def ask_question_to_llm(
    payload: dict[str, Any], timeout_seconds: int, url: str
) -> dict[str, Any]:
    """Appelle le LLM local compatible chat completions.

    Args:
        payload: Corps JSON envoyé au LLM.
        timeout_seconds: Timeout HTTP de l'appel.
        url: Endpoint HTTP du LLM local.

    Returns:
        Réponse JSON décodée du LLM.

    Raises:
        LlmApiException: Si le LLM répond en erreur ou n'est pas joignable.
        ValueError: Si la réponse HTTP n'est pas un JSON valide.
    """
    start = time.perf_counter()
    operation = "local_llm"

    with tracer.start_as_current_span("orchestrator.call_local_llm"):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exception:
            _record_external_error("llm", operation, "timeout", start)
            raise LlmApiException(
                message="Timeout lors de l'appel au LLM local",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("llm", operation, "connect_error", start)
            raise LlmApiException(
                message="Impossible de se connecter au LLM local",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.HTTPStatusError as exception:
            _record_external_error("llm", operation, "http_status", start)
            raise LlmApiException(
                message=f"Erreur HTTP {exception.response.status_code}",
                details={
                    "url": url,
                    "error": f"{str(exception)} ; {exception.response.text}",
                },
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("llm", operation, "request_error", start)
            raise LlmApiException(
                message="Erreur réseau lors de l'appel au LLM local",
                details={"url": url, "error": str(exception)},
            ) from exception

    _record_external_success("llm", operation, start)
    return data


async def ask_question_to_api(
    payload: dict[str, Any], url: str, api_key: str | None
) -> dict[str, Any]:
    """Appelle une API LLM externe compatible avec le provider configuré.

    Args:
        payload: Corps JSON envoyé à l'API LLM.
        url: Endpoint HTTP de l'API LLM.
        api_key: Clé API optionnelle, jamais loggée.

    Returns:
        Réponse JSON décodée du LLM.

    Raises:
        LlmApiException: Si l'API répond en erreur ou n'est pas joignable.
        ValueError: Si la réponse HTTP n'est pas un JSON valide.
    """
    start = time.perf_counter()
    operation = "api_llm"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    with tracer.start_as_current_span("orchestrator.call_api_llm"):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exception:
            _record_external_error("llm", operation, "http_status", start)
            try:
                response_json = exception.response.json()
                raise LlmApiException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={"url": url, "error": str(exception)},
                    original_exception=response_json,
                ) from exception
            except ValueError:
                raise LlmApiException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={
                        "url": url,
                        "error": f"{str(exception)} ; {exception.response.text}",
                    },
                ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("llm", operation, "connect_error", start)
            raise LlmApiException(
                message="Impossible de se connecter à l'API du LLM",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("llm", operation, "timeout", start)
            raise LlmApiException(
                message="Timeout lors de l'appel à l'API du LLM",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("llm", operation, "request_error", start)
            raise LlmApiException(
                message="Erreur réseau lors de l'appel à l'API du LLM",
                details={"url": url, "error": str(exception)},
            ) from exception

    _record_external_success("llm", operation, start)
    return data


def _record_external_success(dependency: str, operation: str, start: float) -> None:
    """Enregistre la durée d'un appel externe réussi.

    Args:
        dependency: Nom stable de la dépendance appelée.
        operation: Nom stable de l'opération appelée.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    orchestrator_external_call_duration_seconds.labels(
        dependency=dependency, operation=operation, status="success"
    ).observe(time.perf_counter() - start)


def _record_external_error(
    dependency: str, operation: str, error_type: str, start: float
) -> None:
    """Enregistre une erreur d'appel externe.

    Args:
        dependency: Nom stable de la dépendance appelée.
        operation: Nom stable de l'opération appelée.
        error_type: Type d'erreur à faible cardinalité.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    orchestrator_external_call_errors_total.labels(
        dependency=dependency, operation=operation, error_type=error_type
    ).inc()
    orchestrator_external_call_duration_seconds.labels(
        dependency=dependency, operation=operation, status="error"
    ).observe(time.perf_counter() - start)
