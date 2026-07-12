import time

from fastapi import APIRouter, Depends
from opentelemetry import trace

from app.api.dependencies import (
    get_config,
    get_vector_store_repository,
    get_wikis_collection,
)
from app.domain.models.retrieve_chunks_request_model import RetrieveChunksRequestBase
from app.domain.models.retrieve_chunks_request_model import (
    RetrieveDocumentChunksRequestBase,
)
from app.domain.models.vector_store_item_model import VectorStoreItemsBase
from app.schemas.retrieve_chunks_response_schema import RetrievedChunksModelBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.core.metrics import (
    SERVICE_NAME,
    rag_errors_total,
    rag_request_duration_seconds,
    rag_requests_total,
    retriever_duration_seconds,
    retriever_errors_total,
    retriever_requests_total,
)
from app.services.manage_collection_service import delete_collection
from app.services.retrieval_service import retrieve_chunks, retrieve_document_chunks
from app.services.saving_service import save_items

router = APIRouter()
tracer = trace.get_tracer(__name__)


@router.post("/save_items", response_model=SaveItemsResponseBase)
def save_items_route(
    items: VectorStoreItemsBase,
    vector_store_repository=Depends(get_vector_store_repository),
) -> SaveItemsResponseBase:
    """Sauvegarde ou met à jour des items vectoriels dans ChromaDB.

    Args:
        items: Documents, embeddings, ids et métadonnées à persister.
        vector_store_repository: Repository ChromaDB injecté par FastAPI.

    Returns:
        Résumé des items sauvegardés et de la taille de collection.

    Raises:
        RetrieverContainerCustomException: Si ChromaDB échoue ou retourne un format inattendu.
    """
    start = time.perf_counter()
    operation = "save_items"
    with tracer.start_as_current_span("retriever.save_items"):
        try:
            response: SaveItemsResponseBase = save_items(items, vector_store_repository)
        except Exception as exception:
            _record_route_error(operation, type(exception).__name__, start)
            raise

    _record_route_success(operation, start)
    return response


@router.post("/retrieve_chunks", response_model=RetrievedChunksModelBase)
def retrieve_chunk_route(
    request_data: RetrieveChunksRequestBase,
    wikis_collection=Depends(get_wikis_collection),
    config=Depends(get_config),
    vector_store_repository=Depends(get_vector_store_repository),
) -> RetrievedChunksModelBase:
    """Recherche les chunks les plus proches d'un embedding de question.

    Args:
        request_data: Requête contenant l'embedding de la question.
        wikis_collection: Collection ChromaDB injectée par FastAPI.
        config: Configuration du retriever.
        vector_store_repository: Repository ChromaDB injecté par FastAPI.

    Returns:
        Chunks filtrés, formatés et triés par similarité décroissante.

    Raises:
        RetrieverContainerCustomException: Si ChromaDB échoue ou retourne un format inattendu.
    """
    start = time.perf_counter()
    operation = "retrieve_chunks"
    with tracer.start_as_current_span("retriever.retrieve_chunks"):
        try:
            response: RetrievedChunksModelBase = retrieve_chunks(
                config,
                wikis_collection,
                request_data.embeded_question,
                vector_store_repository,
            )
        except Exception as exception:
            _record_route_error(operation, type(exception).__name__, start)
            raise

    _record_route_success(operation, start)
    return response


@router.post("/retrieve_document_chunks", response_model=RetrievedChunksModelBase)
def retrieve_document_chunks_route(
    request_data: RetrieveDocumentChunksRequestBase,
    wikis_collection=Depends(get_wikis_collection),
    vector_store_repository=Depends(get_vector_store_repository),
) -> RetrievedChunksModelBase:
    """Récupère les chunks complets des documents demandés.

    Args:
        request_data: Requête contenant les chemins de documents.
        wikis_collection: Collection ChromaDB injectée par FastAPI.
        vector_store_repository: Repository ChromaDB injecté par FastAPI.

    Returns:
        Chunks correspondant aux chemins demandés, triés par index.

    Raises:
        RetrieverContainerCustomException: Si ChromaDB échoue ou retourne un format inattendu.
    """
    start = time.perf_counter()
    operation = "retrieve_document_chunks"
    with tracer.start_as_current_span("retriever.retrieve_document_chunks"):
        try:
            response: RetrievedChunksModelBase = retrieve_document_chunks(
                wikis_collection, request_data.paths, vector_store_repository
            )
        except Exception as exception:
            _record_route_error(operation, type(exception).__name__, start)
            raise

    _record_route_success(operation, start)
    return response


@router.post("/delete_collection")
def delete_collection_route(
    vector_store_repository=Depends(get_vector_store_repository),
    config=Depends(get_config),
) -> str:
    """Supprime puis recrée la collection configurée.

    Args:
        vector_store_repository: Repository ChromaDB injecté par FastAPI.
        config: Configuration contenant le nom de collection.

    Returns:
        Message de confirmation compatible avec le comportement existant.

    Raises:
        RetrieverContainerCustomException: Si ChromaDB échoue pendant la suppression ou recréation.
    """
    start = time.perf_counter()
    operation = "delete_collection"
    with tracer.start_as_current_span("retriever.delete_collection"):
        try:
            delete_collection(config, vector_store_repository)
        except Exception as exception:
            _record_route_error(operation, type(exception).__name__, start)
            raise

    _record_route_success(operation, start)
    return "Collection : bien supprimée."


def _record_route_success(operation: str, start: float) -> None:
    """Enregistre les métriques d'une route retriever réussie.

    Args:
        operation: Nom stable de l'opération métier.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    duration_seconds = time.perf_counter() - start
    retriever_requests_total.labels(operation=operation, status="success").inc()
    retriever_duration_seconds.labels(operation=operation, status="success").observe(
        duration_seconds
    )
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(duration_seconds)


def _record_route_error(operation: str, error_type: str, start: float) -> None:
    """Enregistre les métriques d'une route retriever échouée.

    Args:
        operation: Nom stable de l'opération métier.
        error_type: Type d'erreur à faible cardinalité.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    duration_seconds = time.perf_counter() - start
    retriever_requests_total.labels(operation=operation, status="error").inc()
    retriever_errors_total.labels(operation=operation, error_type=error_type).inc()
    retriever_duration_seconds.labels(operation=operation, status="error").observe(
        duration_seconds
    )
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).inc()
    rag_errors_total.labels(
        service=SERVICE_NAME, operation=operation, error_type=error_type
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).observe(duration_seconds)
