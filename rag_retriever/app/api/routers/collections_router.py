from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_config,
    get_vector_store_repository,
    get_wikis_collection,
)
from app.domain.models.retrieve_chunks_request_model import RetrieveChunksRequestBase
from app.domain.models.vector_store_item_model import VectorStoreItemsBase
from app.schemas.retrieve_chunks_response_schema import RetrievedChunksModelBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.services.manage_collection_service import delete_collection
from app.services.retrieval_service import retrieve_chunks
from app.services.saving_service import save_items

router = APIRouter()


@router.post("/save_items", response_model=SaveItemsResponseBase)
def save_items_route(
    items: VectorStoreItemsBase,
    vector_store_repository=Depends(get_vector_store_repository),
) -> SaveItemsResponseBase:
    response: SaveItemsResponseBase = save_items(items, vector_store_repository)

    return response


@router.post("/retrieve_chunks", response_model=RetrievedChunksModelBase)
def retrieve_chunk_route(
    request_data: RetrieveChunksRequestBase,
    wikis_collection=Depends(get_wikis_collection),
    config=Depends(get_config),
    vector_store_repository=Depends(get_vector_store_repository),
) -> RetrievedChunksModelBase:
    response: RetrievedChunksModelBase = retrieve_chunks(
        config, wikis_collection, request_data.embeded_question, vector_store_repository
    )

    return response


@router.post("/delete_collection")
def delete_collection_route(
    vector_store_repository=Depends(get_vector_store_repository),
    config=Depends(get_config),
) -> str:
    delete_collection(config, vector_store_repository)

    return "Collection : bien supprimée."
