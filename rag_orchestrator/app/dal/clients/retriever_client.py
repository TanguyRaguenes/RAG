import os
import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.exceptions import RetrieverContainerException
from app.core.metrics import (
    orchestrator_external_call_duration_seconds,
    orchestrator_external_call_errors_total,
)

tracer = trace.get_tracer(__name__)


async def retrieve_chunks(embeded_question: list[float]) -> list[dict[str, Any]]:
    """Récupère les chunks candidats auprès du retriever.

    Args:
        embeded_question: Embedding de la question utilisateur.

    Returns:
        Liste de chunks retournée par `rag_retriever`.

    Raises:
        RetrieverContainerException: Si l'URL manque, si le retriever échoue, ou si l'appel HTTP échoue.
        KeyError: Si la réponse JSON ne contient pas `chunks`.
    """
    return await _post_retriever(
        env_var="RAG_RETRIEVER_RETRIEVE_CHUNKS_URL",
        payload={"embeded_question": embeded_question},
        operation="retrieve_chunks",
    )


async def retrieve_document_chunks(paths: list[str]) -> list[dict[str, Any]]:
    """Récupère tous les chunks des documents sélectionnés.

    Args:
        paths: Chemins de documents à récupérer.

    Returns:
        Liste de chunks documentaires retournée par `rag_retriever`.

    Raises:
        RetrieverContainerException: Si l'URL manque, si le retriever échoue, ou si l'appel HTTP échoue.
        KeyError: Si la réponse JSON ne contient pas `chunks`.
    """
    return await _post_retriever(
        env_var="RAG_RETRIEVER_RETRIEVE_DOCUMENT_CHUNKS_URL",
        payload={"paths": paths},
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
        KeyError: Si la réponse JSON ne contient pas `chunks`.
    """
    url = os.getenv(env_var)
    if not url:
        raise RetrieverContainerException(
            message="URL du service 'retriever' non configurée",
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
            try:
                response_json = exception.response.json()
                raise RetrieverContainerException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={"url": url, "error": str(exception)},
                    original_exception=response_json,
                ) from exception
            except ValueError:
                raise RetrieverContainerException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={"url": url, "error": str(exception)},
                ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("retriever", operation, "connect_error", start)
            raise RetrieverContainerException(
                message="Impossible de se connecter au service 'retriever'",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("retriever", operation, "timeout", start)
            raise RetrieverContainerException(
                message="Timeout lors de l'appel au service 'retriever'",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("retriever", operation, "request_error", start)
            raise RetrieverContainerException(
                message="Erreur réseau lors de l'appel au service 'retriever'",
                details={"url": url, "error": str(exception)},
            ) from exception

    orchestrator_external_call_duration_seconds.labels(
        dependency="retriever", operation=operation, status="success"
    ).observe(time.perf_counter() - start)

    return data["chunks"]


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
