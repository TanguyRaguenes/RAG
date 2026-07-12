import logging
import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.exceptions import (
    RerankingResponseFormatException,
    RerankingServiceException,
)
from app.core.metrics import (
    SERVICE_NAME,
    rag_errors_total,
    rag_request_duration_seconds,
    rag_requests_total,
    reranking_duration_seconds,
    reranking_errors_total,
    reranking_requests_total,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def score_chunks(
    question: str,
    chunks: list[dict[str, Any]],
    config: dict,
) -> dict[int, float]:
    """Demande au moteur de reranking de scorer les chunks candidats.

    Args:
        question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
        chunks: Chunks documentaires manipulés par le pipeline RAG.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Scores de reranking alignés avec la liste de chunks fournie.

    Raises:
        RerankingServiceException: Si le service de reranking est indisponible ou retourne une erreur.
        RerankingResponseFormatException: Si la réponse du reranker ne contient pas les scores attendus.
    """
    start_time = time.perf_counter()
    operation = "score_chunks"
    reranking_requests_total.inc()

    url: str = config["reranking"]["url"]
    model: str = config["reranking"]["model"]
    timeout_seconds: int = config["reranking"].get("timeout_seconds", 180)
    max_chunk_chars: int = config["reranking"].get("max_chunk_chars", 1600)

    logger.info(
        "Reranking request started",
        extra={
            "group": "reranking",
            "event": "request_started",
            "chunk_count": len(chunks),
            "question_length": len(question),
            "model": model,
        },
    )

    payload = _build_payload(question, chunks, max_chunk_chars)

    try:
        with tracer.start_as_current_span("reranking.call_model") as span:
            span.set_attribute("reranking.model", model)
            span.set_attribute("reranking.chunk_count", len(chunks))
            span.set_attribute("reranking.question_length", len(question))
            span.set_attribute("http.url", url)

            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

    except httpx.HTTPStatusError as e:
        reranking_errors_total.inc()
        _record_request_error(operation, "http_status", start_time)
        logger.exception(
            "Reranking request failed",
            extra={
                "group": "reranking",
                "event": "request_failed",
                "error_type": "http_status",
                "status_code": e.response.status_code,
                "url": str(e.request.url),
            },
        )
        raise RerankingServiceException(
            message=f"Erreur HTTP {e.response.status_code}",
            details={"url": str(e.request.url), "response": e.response.text},
        ) from e

    except httpx.ConnectError as e:
        reranking_errors_total.inc()
        _record_request_error(operation, "connect_error", start_time)
        logger.exception(
            "Reranking request failed",
            extra={
                "group": "reranking",
                "event": "request_failed",
                "error_type": "connect_error",
                "url": url,
                "error": str(e),
            },
        )
        raise RerankingServiceException(
            message="Impossible de se connecter au service 'reranker'",
            details={"url": url, "error": str(e)},
        ) from e

    except httpx.TimeoutException as e:
        reranking_errors_total.inc()
        _record_request_error(operation, "timeout", start_time)
        logger.exception(
            "Reranking request failed",
            extra={
                "group": "reranking",
                "event": "request_failed",
                "error_type": "timeout",
                "url": url,
                "error": str(e),
            },
        )
        raise RerankingServiceException(
            message="Timeout lors de l'appel au service 'reranker'",
            details={"url": url, "error": str(e)},
        ) from e

    except httpx.RequestError as e:
        reranking_errors_total.inc()
        _record_request_error(operation, "request_error", start_time)
        logger.exception(
            "Reranking request failed",
            extra={
                "group": "reranking",
                "event": "request_failed",
                "error_type": "request_error",
                "url": url,
                "error": str(e),
            },
        )
        raise RerankingServiceException(
            message="Erreur réseau lors de l'appel au service 'reranker'",
            details={"url": url, "error": str(e)},
        ) from e

    except ValueError as e:
        reranking_errors_total.inc()
        _record_request_error(operation, "invalid_json", start_time)
        raise RerankingResponseFormatException(
            message="La réponse TEI n'est pas un JSON valide",
            details={"url": url},
        ) from e

    try:
        scores = _parse_scores(data, len(chunks))
    except RerankingResponseFormatException:
        reranking_errors_total.inc()
        _record_request_error(operation, "response_format", start_time)
        logger.exception(
            "Reranking response parsing failed",
            extra={
                "group": "reranking",
                "event": "response_parsing_failed",
                "model": model,
                "chunk_count": len(chunks),
            },
        )
        raise

    duration_seconds = time.perf_counter() - start_time
    duration_ms = round(duration_seconds * 1000, 2)

    reranking_duration_seconds.observe(duration_seconds)
    _record_request_success(operation, duration_seconds)

    logger.info(
        "Reranking request completed",
        extra={
            "group": "reranking",
            "event": "request_completed",
            "duration_ms": duration_ms,
            "model": model,
            "chunk_count": len(chunks),
        },
    )

    return scores


def _record_request_success(operation: str, duration_seconds: float) -> None:
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(duration_seconds)


def _record_request_error(operation: str, error_type: str, start_time: float) -> None:
    duration_seconds = time.perf_counter() - start_time
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).inc()
    rag_errors_total.labels(
        service=SERVICE_NAME, operation=operation, error_type=error_type
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).observe(duration_seconds)


def _build_payload(
    question: str,
    chunks: list[dict[str, Any]],
    max_chunk_chars: int,
) -> dict[str, Any]:
    """Construit le payload envoyé au serveur de reranking TEI.

    Args:
        question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
        chunks: Chunks documentaires manipulés par le pipeline RAG.
        max_chunk_chars: Longueur maximale de chaque chunk envoyé au reranker.

    Returns:
        Payload JSON compatible avec l'endpoint TEI de reranking.
    """
    return {
        "query": question,
        "texts": [chunk.get("document", "")[:max_chunk_chars] for chunk in chunks],
        "raw_scores": False,
        "return_text": False,
    }


def _parse_scores(data: Any, expected_chunk_count: int) -> dict[int, float]:
    """Extrait les scores numériques depuis la réponse du reranker.

    Args:
        data: Données brutes à transformer ou valider.
        expected_chunk_count: Nombre de chunks attendus pour valider la réponse du reranker.

    Returns:
        Scores numériques extraits et ordonnés par index de chunk.

    Raises:
        RerankingResponseFormatException: Si la réponse du reranker ne contient pas les scores attendus.
    """
    raw_scores = data.get("results") if isinstance(data, dict) else data
    if not isinstance(raw_scores, list):
        raise RerankingResponseFormatException(
            message="La réponse TEI ne contient pas de liste de scores exploitable",
            details={"response": data},
        )

    scores: dict[int, float] = {}
    for item in raw_scores:
        if not isinstance(item, dict):
            raise RerankingResponseFormatException(
                message="Un score de reranking est invalide",
                details={"item": item},
            )

        index = item.get("index")
        score = item.get("score")

        if not isinstance(index, int) or index < 0 or index >= expected_chunk_count:
            raise RerankingResponseFormatException(
                message="Un index de score de reranking est invalide",
                details={"index": index, "expected_chunk_count": expected_chunk_count},
            )

        if not isinstance(score, int | float):
            raise RerankingResponseFormatException(
                message="Un score de reranking est invalide",
                details={"index": index, "score": score},
            )

        scores[index] = max(0.0, min(1.0, float(score)))

    return scores
