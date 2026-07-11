import json
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
    reranking_requests_total.inc()
    start_time = time.perf_counter()

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

    payload = {
        "model": model,
        "prompt": _build_prompt(question, chunks, max_chunk_chars),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

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

    try:
        scores = _parse_scores(data, len(chunks))
    except RerankingResponseFormatException:
        reranking_errors_total.inc()
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


def _build_prompt(
    question: str,
    chunks: list[dict[str, Any]],
    max_chunk_chars: int,
) -> str:
    candidates = [
        {
            "index": index,
            "title": chunk.get("metadata", {}).get("title", ""),
            "path": chunk.get("metadata", {}).get("path", ""),
            "text": chunk.get("document", "")[:max_chunk_chars],
        }
        for index, chunk in enumerate(chunks)
    ]

    return (
        "Tu es un reranker pour un système RAG. "
        "Score chaque chunk selon sa pertinence pour répondre à la question. "
        "Utilise un score entre 0 et 1. "
        "Retourne uniquement un JSON valide au format "
        '{"scores":[{"index":0,"score":0.95}]}.\n\n'
        f"Question:\n{question}\n\n"
        f"Chunks:\n{json.dumps(candidates, ensure_ascii=False)}"
    )


def _parse_scores(data: dict[str, Any], expected_chunk_count: int) -> dict[int, float]:
    raw_response = data.get("response")
    if not isinstance(raw_response, str):
        raise RerankingResponseFormatException(
            message="La réponse Ollama ne contient pas de champ 'response' exploitable",
            details={"response_keys": list(data.keys())},
        )

    try:
        parsed_response = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise RerankingResponseFormatException(
            message="La réponse du modèle de reranking n'est pas un JSON valide",
            details={"response": raw_response},
        ) from e

    raw_scores = parsed_response.get("scores")
    if not isinstance(raw_scores, list):
        raise RerankingResponseFormatException(
            message="La réponse du modèle de reranking ne contient pas de liste 'scores'",
            details={"response": parsed_response},
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
