from fastapi import APIRouter

from app.api.dependencies import RerankServiceDep
from app.schemas.rerank_chunks_request_schema import RerankChunksRequestBase
from app.schemas.rerank_chunks_response_schema import RerankChunksResponseBase

router = APIRouter()


@router.post("/rerank_chunks", response_model=RerankChunksResponseBase)
async def rerank_chunks_route(
    payload: RerankChunksRequestBase,
    service: RerankServiceDep,
) -> RerankChunksResponseBase:
    """Délègue une requête HTTP validée au service de reranking.

    Args:
        payload: Question et chunks validés par Pydantic.
        service: Service métier injecté depuis l'état applicatif.

    Returns:
        Réponse chronométrée contenant les chunks rerankés.

    Raises:
        RerankerContainerCustomException: Si le fournisseur externe échoue.
    """
    return await service.execute(payload)
