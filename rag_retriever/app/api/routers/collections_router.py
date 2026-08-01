from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_config, get_vector_store_repository
from app.core.config import RetrieverConfig
from app.core.operation_observer import observe_retriever_operation
from app.dal.repositories.vector_store_repository import VectorStoreRepository
from app.schemas.retrieve_chunks_request_schema import (
    RetrieveChunksRequestBase,
    RetrieveDocumentChunksRequestBase,
)
from app.schemas.retrieve_chunks_response_schema import RetrievedChunksModelBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase
from app.services.manage_collection_service import delete_collection
from app.services.retrieval_service import retrieve_chunks, retrieve_document_chunks
from app.services.saving_service import save_items

router = APIRouter()

ConfigDep = Annotated[RetrieverConfig, Depends(get_config)]
RepositoryDep = Annotated[VectorStoreRepository, Depends(get_vector_store_repository)]


@router.post("/save_items", response_model=SaveItemsResponseBase)
def save_items_route(
    items: VectorStoreItemsBase,
    config: ConfigDep,
    vector_store_repository: RepositoryDep,
) -> SaveItemsResponseBase:
    """Délègue la persistance d'un lot vectoriel au service métier.

    Args:
        items: Lot vectoriel validé par Pydantic.
        config: Configuration applicative injectée par FastAPI.
        vector_store_repository: Repository injecté sans exposer ChromaDB.

    Returns:
        Résumé public de la sauvegarde.
    """
    with observe_retriever_operation("save_items"):
        return save_items(items, config, vector_store_repository)


@router.post("/retrieve_chunks", response_model=RetrievedChunksModelBase)
def retrieve_chunk_route(
    request_data: RetrieveChunksRequestBase,
    config: ConfigDep,
    vector_store_repository: RepositoryDep,
) -> RetrievedChunksModelBase:
    """Délègue la recherche vectorielle au service de retrieval.

    Args:
        request_data: Embedding de question validé par Pydantic.
        config: Configuration des règles de sélection et de collection.
        vector_store_repository: Repository injecté sans collection technique.

    Returns:
        Chunks pertinents au format HTTP historique.
    """
    with observe_retriever_operation("retrieve_chunks"):
        return retrieve_chunks(
            config,
            request_data.embeded_question,
            vector_store_repository,
        )


@router.post("/retrieve_document_chunks", response_model=RetrievedChunksModelBase)
def retrieve_document_chunks_route(
    request_data: RetrieveDocumentChunksRequestBase,
    config: ConfigDep,
    vector_store_repository: RepositoryDep,
) -> RetrievedChunksModelBase:
    """Délègue la lecture complète de documents au service de retrieval.

    Args:
        request_data: Chemins documentaires validés par Pydantic.
        config: Configuration contenant la collection de lecture.
        vector_store_repository: Repository injecté sans collection technique.

    Returns:
        Chunks documentaires au format HTTP historique.
    """
    with observe_retriever_operation("retrieve_document_chunks"):
        return retrieve_document_chunks(
            config,
            request_data.paths,
            vector_store_repository,
        )


@router.post("/delete_collection")
def delete_collection_route(
    config: ConfigDep,
    vector_store_repository: RepositoryDep,
) -> str:
    """Délègue la réinitialisation de la collection configurée.

    Args:
        config: Configuration contenant la collection à réinitialiser.
        vector_store_repository: Repository injecté pour l'opération de gestion.

    Returns:
        Message de confirmation conservé pour compatibilité HTTP.
    """
    with observe_retriever_operation("delete_collection"):
        delete_collection(config, vector_store_repository)
    return "Collection : bien supprimée."
