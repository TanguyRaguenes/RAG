import logging
import time
from typing import Any, Protocol

import httpx
from opentelemetry import trace
from pydantic import ValidationError

from app.core.config import RerankerConfig, RerankingConfig
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
from app.schemas.rerank_chunks_request_schema import ChunkModelBase
from app.schemas.reranking_provider_schema import RerankingProviderResponse

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class RerankingClient(Protocol):
    """Contrat du fournisseur externe de scores de reranking."""

    async def score(
        self, question: str, chunks: list[ChunkModelBase]
    ) -> dict[int, float]:
        """Score tous les chunks sans perte ni valeur par défaut.

        Args:
            question: Question utilisée comme requête de reranking.
            chunks: Chunks candidats validés par l'API.

        Returns:
            Un score valide pour chaque index de chunk.

        Raises:
            RerankingServiceException: Si le fournisseur est indisponible.
            RerankingResponseFormatException: Si sa réponse est incomplète ou invalide.
        """
        ...


class TeiRerankingClient:
    """Client HTTP du endpoint TEI de reranking."""

    def __init__(self, config: RerankingConfig) -> None:
        """Configure le transport et le contrat TEI.

        Args:
            config: Paramètres validés du fournisseur de reranking.
        """
        self._config = config

    async def score(
        self, question: str, chunks: list[ChunkModelBase]
    ) -> dict[int, float]:
        """Appelle TEI et exige un score par index attendu.

        Args:
            question: Question utilisateur, non journalisée.
            chunks: Chunks validés à scorer dans leur ordre d'origine.

        Returns:
            Mapping exhaustif des index vers les scores TEI.

        Raises:
            RerankingServiceException: Si le transport HTTP échoue.
            RerankingResponseFormatException: Si le JSON ou les scores sont invalides.
        """
        start_time = time.perf_counter()
        operation = "score_chunks"
        reranking_requests_total.inc()

        logger.info(
            "Reranking request started",
            extra={
                "group": "reranking",
                "event": "request_started",
                "chunk_count": len(chunks),
                "question_length": len(question),
                "model": self._config.model,
            },
        )
        payload = _build_payload(
            question, chunks, max_chunk_chars=self._config.max_chunk_chars
        )

        try:
            data = await self._post(payload, len(chunks), start_time)
            scores = _parse_scores(data, len(chunks))
        except RerankingResponseFormatException:
            reranking_errors_total.inc()
            _record_request_error(operation, "response_format", start_time)
            raise

        duration_seconds = time.perf_counter() - start_time
        reranking_duration_seconds.observe(duration_seconds)
        _record_request_success(operation, duration_seconds)
        logger.info(
            "Reranking request completed",
            extra={
                "group": "reranking",
                "event": "request_completed",
                "duration_ms": round(duration_seconds * 1000, 2),
                "model": self._config.model,
                "chunk_count": len(chunks),
            },
        )
        return scores

    async def _post(
        self,
        payload: dict[str, Any],
        chunk_count: int,
        start_time: float,
    ) -> object:
        """Exécute l'appel HTTP TEI avec instrumentation et erreurs sûres.

        Args:
            payload: Corps JSON TEI construit depuis les chunks validés.
            chunk_count: Nombre de chunks utilisé dans la trace.
            start_time: Instant initial utilisé par les métriques d'erreur.

        Returns:
            JSON brut à valider comme réponse TEI.

        Raises:
            RerankingServiceException: Si le statut ou le transport échoue.
            RerankingResponseFormatException: Si la réponse n'est pas du JSON.
        """
        try:
            with tracer.start_as_current_span("reranking.call_model") as span:
                span.set_attribute("reranking.model", self._config.model)
                span.set_attribute("reranking.chunk_count", chunk_count)
                span.set_attribute("http.url", self._config.url)
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds
                ) as client:
                    response = await client.post(self._config.url, json=payload)
                    response.raise_for_status()
                    return response.json()
        except httpx.HTTPStatusError as exception:
            self._raise_transport_error("http_status", exception, start_time)
        except httpx.ConnectError as exception:
            self._raise_transport_error("connect_error", exception, start_time)
        except httpx.TimeoutException as exception:
            self._raise_transport_error("timeout", exception, start_time)
        except httpx.RequestError as exception:
            self._raise_transport_error("request_error", exception, start_time)
        except ValueError as exception:
            raise RerankingResponseFormatException(
                message="La réponse du reranker n'est pas un JSON valide"
            ) from exception
        raise AssertionError("unreachable")

    def _raise_transport_error(
        self,
        error_type: str,
        exception: httpx.RequestError,
        start_time: float,
    ) -> None:
        """Enregistre l'échec technique et lève une erreur API sans fuite.

        Args:
            error_type: Catégorie stable utilisée dans les logs.
            exception: Erreur HTTPX originale conservée comme cause.
            start_time: Instant initial utilisé par les métriques d'erreur.

        Raises:
            RerankingServiceException: Toujours, avec un message externe générique.
        """
        reranking_errors_total.inc()
        _record_request_error("score_chunks", error_type, start_time)
        raise RerankingServiceException(
            message="Le service de reranking est temporairement indisponible",
            internal_message="Échec du transport HTTP vers le reranker",
            internal_details={
                "error_type": error_type,
                "upstream_host": httpx.URL(self._config.url).host or "unknown",
            },
        ) from exception


async def score_chunks(
    question: str,
    chunks: list[dict[str, Any]],
    config: RerankerConfig | dict[str, Any],
) -> dict[int, float]:
    """Préserve la fonction publique en déléguant au client TEI typé.

    Args:
        question: Question utilisée pour le scoring.
        chunks: DTO de chunks à valider avant transport.
        config: Configuration typée ou dictionnaire historique.

    Returns:
        Mapping exhaustif des scores par index.
    """
    try:
        typed_config = RerankerConfig.model_validate(config)
        typed_chunks = [ChunkModelBase.model_validate(chunk) for chunk in chunks]
    except ValidationError as exception:
        raise RerankingResponseFormatException(
            message="Les données de scoring sont invalides",
            internal_message="Validation Pydantic de la frontière historique impossible",
            internal_details={"validation_errors": exception.error_count()},
        ) from exception
    return await TeiRerankingClient(typed_config.reranking).score(
        question, typed_chunks
    )


def _build_payload(
    question: str,
    chunks: list[ChunkModelBase],
    max_chunk_chars: int,
) -> dict[str, Any]:
    """Construit le payload TEI depuis des chunks déjà validés.

    Args:
        question: Requête de reranking.
        chunks: Chunks candidats dans leur ordre d'origine.
        max_chunk_chars: Longueur maximale envoyée par document.

    Returns:
        Payload compatible avec le endpoint TEI `/rerank`.
    """
    return {
        "query": question,
        "texts": [chunk.document[:max_chunk_chars] for chunk in chunks],
        "raw_scores": False,
        "return_text": False,
    }


def _parse_scores(data: object, expected_chunk_count: int) -> dict[int, float]:
    """Valide des scores finis, uniques et exhaustifs pour `0..n-1`.

    Args:
        data: JSON brut TEI, directement sous forme de liste ou dans `results`.
        expected_chunk_count: Nombre exact d'index attendus.

    Returns:
        Mapping complet sans score inventé ni corrigé silencieusement.

    Raises:
        RerankingResponseFormatException: Si un score ou l'ensemble des index est invalide.
    """
    raw_scores = data.get("results") if isinstance(data, dict) else data
    try:
        response = RerankingProviderResponse.model_validate(raw_scores)
    except (ValidationError, TypeError) as exception:
        raise RerankingResponseFormatException(
            message="La réponse du reranker contient des scores invalides",
            internal_message="Validation Pydantic de la réponse TEI impossible",
            internal_details={
                "validation_errors": (
                    exception.error_count()
                    if isinstance(exception, ValidationError)
                    else 1
                )
            },
        ) from exception

    indexes = [item.index for item in response.root]
    unique_indexes = set(indexes)
    expected_indexes = set(range(expected_chunk_count))
    if len(indexes) != len(unique_indexes):
        raise RerankingResponseFormatException(
            message="La réponse du reranker contient des index dupliqués"
        )
    if unique_indexes != expected_indexes:
        raise RerankingResponseFormatException(
            message="La réponse du reranker n'est pas exhaustive",
            details={
                "expected_count": expected_chunk_count,
                "received_count": len(unique_indexes),
            },
        )
    return {item.index: item.score for item in response.root}


def _record_request_success(operation: str, duration_seconds: float) -> None:
    """Enregistre une requête externe réussie.

    Args:
        operation: Nom stable de l'opération.
        duration_seconds: Durée complète du scoring.
    """
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(duration_seconds)


def _record_request_error(operation: str, error_type: str, start_time: float) -> None:
    """Enregistre une réponse externe invalide.

    Args:
        operation: Nom stable de l'opération.
        error_type: Catégorie stable de l'erreur.
        start_time: Instant de début utilisé pour calculer la durée.
    """
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
