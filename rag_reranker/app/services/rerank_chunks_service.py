import time
from typing import Any

from pydantic import ValidationError

from app.core.config import RerankerConfig
from app.core.exceptions import RerankingResponseFormatException
from app.dal.clients.reranking_client import RerankingClient, TeiRerankingClient
from app.schemas.rerank_chunks_request_schema import (
    ChunkModelBase,
    RerankChunksRequestBase,
)
from app.schemas.rerank_chunks_response_schema import (
    RerankChunksResponseBase,
    RerankedChunkModelBase,
)


class RerankChunksService:
    """Orchestre le reranking sans dépendre du transport HTTP concret."""

    def __init__(self, config: RerankerConfig, client: RerankingClient) -> None:
        """Injecte la configuration métier et le fournisseur de scores.

        Args:
            config: Configuration validée contenant notamment `top_k`.
            client: Frontière externe chargée de scorer tous les chunks.
        """
        self._config = config
        self._client = client

    async def execute(
        self, payload: RerankChunksRequestBase
    ) -> RerankChunksResponseBase:
        """Exécute une requête complète et construit sa réponse chronométrée.

        Args:
            payload: Requête HTTP déjà validée par Pydantic.

        Returns:
            Chunks rerankés et durée de traitement publique.

        Raises:
            RerankerContainerCustomException: Si le fournisseur externe échoue.
        """
        start = time.perf_counter()
        chunks = await self.rerank(payload.question, payload.chunks)
        elapsed = time.perf_counter() - start
        minutes, seconds = divmod(int(elapsed), 60)
        return RerankChunksResponseBase(
            duration_ms=round(elapsed * 1000, 2),
            duration_human=f"{minutes:02d}:{seconds:02d}",
            reranked_chunks=chunks,
        )

    async def rerank(
        self, question: str, chunks: list[ChunkModelBase]
    ) -> list[RerankedChunkModelBase]:
        """Trie les chunks à partir d'un mapping de scores exhaustif.

        Args:
            question: Question utilisée pour mesurer la pertinence.
            chunks: Chunks candidats validés dans leur ordre d'origine.

        Returns:
            Chunks enrichis dont le score ne serait pas affiché comme `0.00`, triés
            puis limités à `top_k`.

        Raises:
            RerankerContainerCustomException: Si aucun score complet n'est disponible.
        """
        if not chunks or self._config.reranking.top_k == 0:
            return []

        scores = await self._client.score(question, chunks)
        expected_indexes = set(range(len(chunks)))
        if set(scores) != expected_indexes:
            raise RerankingResponseFormatException(
                message="La réponse du reranker n'est pas exhaustive",
                details={
                    "expected_count": len(chunks),
                    "received_count": len(scores),
                },
            )
        try:
            scored_chunks = [
                RerankedChunkModelBase(
                    **chunk.model_dump(),
                    rerank_score=scores[index],
                )
                for index, chunk in enumerate(chunks)
            ]
        except ValidationError as exception:
            raise RerankingResponseFormatException(
                message="La réponse du reranker contient des scores invalides",
                internal_message="Validation Pydantic des chunks rerankés impossible",
                internal_details={"validation_errors": exception.error_count()},
            ) from exception
        positive_score_chunks = (
            chunk
            for chunk in scored_chunks
            if chunk.rerank_score >= self._config.reranking.minimum_rerank_score
        )
        return sorted(
            positive_score_chunks,
            key=lambda chunk: (chunk.rerank_score, chunk.similarity),
            reverse=True,
        )[: self._config.reranking.top_k]


async def rerank_chunks(
    question: str,
    chunks: list[dict[str, Any]],
    config: RerankerConfig | dict[str, Any],
) -> list[dict[str, Any]]:
    """Préserve la fonction publique historique autour du service typé.

    Args:
        question: Question utilisée pour le reranking.
        chunks: Chunks sérialisés reçus par les appelants existants.
        config: Configuration typée ou dictionnaire historique.

    Returns:
        Chunks rerankés sérialisés comme auparavant.
    """
    try:
        typed_config = RerankerConfig.model_validate(config)
        typed_chunks = [ChunkModelBase.model_validate(chunk) for chunk in chunks]
    except ValidationError as exception:
        raise RerankingResponseFormatException(
            message="Les données de reranking sont invalides",
            internal_message="Validation Pydantic de la frontière historique impossible",
            internal_details={"validation_errors": exception.error_count()},
        ) from exception
    client = TeiRerankingClient(typed_config.reranking)
    service = RerankChunksService(typed_config, client)
    result = await service.rerank(question, typed_chunks)
    return [chunk.model_dump() for chunk in result]
