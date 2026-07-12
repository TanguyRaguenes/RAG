import time
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_config
from app.domain.models.rerank_chunks_request_model import RerankChunksRequestBase
from app.schemas.rerank_chunks_response_schema import RerankChunksResponseBase
from app.services.rerank_chunks_service import rerank_chunks as service_rerank_chunks

router = APIRouter()

ConfigDep = Annotated[dict, Depends(get_config)]


@router.post("/rerank_chunks")
async def rerank_chunks_route(
    payload: RerankChunksRequestBase,
    config: ConfigDep,
) -> RerankChunksResponseBase:
    """Expose l'endpoint HTTP de reranking des chunks.

    Args:
        payload: Corps JSON transmis à une API externe ou persisté en base.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Réponse HTTP contenant la durée et les chunks rerankés.
    """
    start: float = time.perf_counter()

    reranked_chunks = await service_rerank_chunks(
        payload.question,
        [chunk.model_dump() for chunk in payload.chunks],
        config,
    )

    elapsed: float = time.perf_counter() - start
    duration_ms = round(elapsed * 1000, 2)

    minutes, seconds = divmod(int(elapsed), 60)
    duration_human: str = f"{minutes:02d}:{seconds:02d}"

    return RerankChunksResponseBase(
        duration_ms=duration_ms,
        duration_human=duration_human,
        reranked_chunks=reranked_chunks,
    )
