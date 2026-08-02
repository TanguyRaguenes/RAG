import os
import time
from typing import Any, Literal

import httpx
from opentelemetry import trace

from app.core.exceptions import DependencyResponseError, RetrieverContainerException
from app.core.metrics import (
    orchestrator_external_call_duration_seconds,
    orchestrator_external_call_errors_total,
)

tracer = trace.get_tracer(__name__)


async def retrieve_chunks(
    embeded_question: list[float],
    collection_profile: Literal["default", "evaluation"] = "default",
) -> list[dict[str, Any]]:
    """Récupère les chunks candidats auprès du retriever.

    Args:
        embeded_question: Embedding de la question utilisateur.
        collection_profile: Profil fixe de collection à interroger.

    Returns:
        Liste de chunks retournée par `rag_retriever`.

    Raises:
        RetrieverContainerException: Si l'URL manque, si le retriever échoue, ou si l'appel HTTP échoue.
        DependencyResponseError: Si la réponse JSON ne contient pas les chunks attendus.
    """
    return await _post_retriever(
        env_var="RAG_RETRIEVER_RETRIEVE_CHUNKS_URL",
        payload={
            "embeded_question": embeded_question,
            "collection_profile": collection_profile,
        },
        operation="retrieve_chunks",
    )


async def retrieve_document_chunks(
    paths: list[str],
    collection_profile: Literal["default", "evaluation"] = "default",
) -> list[dict[str, Any]]:
    """Récupère tous les chunks des documents sélectionnés.

    Args:
        paths: Chemins de documents à récupérer.
        collection_profile: Profil fixe de collection à interroger.

    Returns:
        Liste de chunks documentaires retournée par `rag_retriever`.

    Raises:
        RetrieverContainerException: Si l'URL manque, si le retriever échoue, ou si l'appel HTTP échoue.
        DependencyResponseError: Si la réponse JSON ne contient pas les chunks attendus.
    """
    return await _post_retriever(
        env_var="RAG_RETRIEVER_RETRIEVE_DOCUMENT_CHUNKS_URL",
        payload={"paths": paths, "collection_profile": collection_profile},
        operation="retrieve_document_chunks",
    )


async def _post_retriever(
    *, env_var: str, payload: dict[str, Any], operation: str
) -> list[dict[str, Any]]:
    """Envoie une requête POST au service retriever.

    Args:
        env_var: Nom de la variable d'environnement contenant l'URL cible.
        payload: Corps JSON envoyé au retriever.
        operation: Nom stable de l'opération appelée.

    Returns:
        Liste de chunks issue du champ `chunks` de la réponse.

    Raises:
        RetrieverContainerException: Si l'URL manque ou si l'appel échoue.
        DependencyResponseError: Si la réponse JSON ne contient pas les chunks attendus.
    """
    url = os.getenv(env_var)
    if not url:
        raise RetrieverContainerException(
            internal_message="Retriever URL is not configured",
            details={"env_var": env_var},
        )

    start = time.perf_counter()
    with tracer.start_as_current_span(f"orchestrator.call_retriever.{operation}"):
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exception:
            _record_external_error("retriever", operation, "http_status", start)
            raise RetrieverContainerException(
                internal_message="Retriever returned an HTTP error",
                details={"status_code": exception.response.status_code},
            ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("retriever", operation, "connect_error", start)
            raise RetrieverContainerException(
                internal_message="Retriever connection failed",
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("retriever", operation, "timeout", start)
            raise RetrieverContainerException(
                internal_message="Retriever request timed out",
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("retriever", operation, "request_error", start)
            raise RetrieverContainerException(
                internal_message="Retriever request failed",
            ) from exception
        except ValueError as exception:
            _record_external_error("retriever", operation, "invalid_json", start)
            raise DependencyResponseError(
                "Retriever returned invalid JSON",
                details={"dependency": "retriever", "operation": operation},
            ) from exception

    try:
        chunks = _extract_chunks(data, operation)
    except DependencyResponseError:
        _record_external_error("retriever", operation, "invalid_response", start)
        raise

    orchestrator_external_call_duration_seconds.labels(
        dependency="retriever", operation=operation, status="success"
    ).observe(time.perf_counter() - start)
    return chunks


def _extract_chunks(data: object, operation: str) -> list[dict[str, Any]]:
    """Valide le champ ``chunks`` d'une réponse retriever.

    Args:
        data: JSON décodé retourné par le retriever.
        operation: Opération retriever utilisée pour le diagnostic interne.

    Returns:
        Liste de chunks représentés par des objets JSON.

    Raises:
        DependencyResponseError: Si le champ est absent ou mal typé.
    """
    if not isinstance(data, dict):
        raise DependencyResponseError(
            "Retriever response is not an object",
            details={"dependency": "retriever", "operation": operation},
        )

    try:
        chunks = data["chunks"]
    except (KeyError, TypeError) as exception:
        raise DependencyResponseError(
            "Retriever response is missing chunks",
            details={"dependency": "retriever", "operation": operation},
        ) from exception

    if not isinstance(chunks, list) or not all(
        isinstance(chunk, dict) and isinstance(chunk.get("metadata", {}), dict)
        for chunk in chunks
    ):
        raise DependencyResponseError(
            "Retriever response contains malformed chunks",
            details={"dependency": "retriever", "operation": operation},
        )
    return chunks


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
