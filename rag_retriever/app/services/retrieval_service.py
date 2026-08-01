from app.core.config import RetrieverConfig
from app.core.exceptions import RetrievalFormatException
from app.core.metrics import retriever_chunks_total
from app.domain.models.vector_store_model import RetrievedChunk
from app.domain.vector_store_repository import VectorStoreRepositoryProtocol
from app.schemas.retrieve_chunks_response_schema import (
    ChunkModelBase,
    RetrievedChunksModelBase,
)
from app.schemas.vector_db_items_schema import VectorMetadataBase


def retrieve_chunks(
    config: RetrieverConfig,
    embeded_question: list[float],
    vector_store_repository: VectorStoreRepositoryProtocol,
) -> RetrievedChunksModelBase:
    """Recherche, filtre et classe les chunks pertinents pour une question.

    Args:
        config: Configuration de collection et règles de sélection du retriever.
        embeded_question: Embedding de la question utilisateur.
        vector_store_repository: Port chargé uniquement des accès au stockage.

    Returns:
        Chunks respectant le seuil, le minimum et le tri métier.

    Raises:
        RetrievalFormatException: Si un résultat métier ne peut pas être exposé.
    """
    collection_name: str = config["collection"]["name"]
    retrieval_config = config["retriever"]
    top_k: int = retrieval_config["top_k"]
    minimum_similarity: float = retrieval_config["minimum_similarity"]
    minimum_number_of_chunks: int = retrieval_config["minimum_number_of_chunks"]

    retrieved_chunks = vector_store_repository.query_chunks(
        collection_name,
        embeded_question,
        top_k,
    )

    selected_chunks = select_relevant_chunks(
        retrieved_chunks,
        minimum_similarity,
        minimum_number_of_chunks,
    )
    retriever_chunks_total.labels(operation="retrieve_chunks").inc(len(selected_chunks))
    return RetrievedChunksModelBase(
        chunks=[format_retrieved_chunk(chunk) for chunk in selected_chunks]
    )


def retrieve_document_chunks(
    config: RetrieverConfig,
    paths: list[str],
    vector_store_repository: VectorStoreRepositoryProtocol,
) -> RetrievedChunksModelBase:
    """Récupère les chunks complets de documents dans un ordre déterministe.

    Args:
        config: Configuration contenant le nom de la collection source.
        paths: Chemins demandés, potentiellement dupliqués.
        vector_store_repository: Port chargé uniquement des accès au stockage.

    Returns:
        Chunks regroupés selon l'ordre des chemins puis leur index.

    Raises:
        RetrievalFormatException: Si un résultat métier ne peut pas être exposé.
    """
    collection_name: str = config["collection"]["name"]
    unique_paths = list(dict.fromkeys(paths))
    document_chunks = vector_store_repository.get_chunks_by_paths(
        collection_name,
        unique_paths,
    )

    path_order = {path: index for index, path in enumerate(unique_paths)}
    ordered_chunks = sorted(
        document_chunks,
        key=lambda chunk: (
            path_order.get(chunk.metadata.path, len(path_order)),
            chunk.metadata.chunk_index,
        ),
    )
    retriever_chunks_total.labels(operation="retrieve_document_chunks").inc(
        len(ordered_chunks)
    )
    return RetrievedChunksModelBase(
        chunks=[format_retrieved_chunk(chunk) for chunk in ordered_chunks]
    )


def select_relevant_chunks(
    chunks: list[RetrievedChunk],
    minimum_similarity: float,
    minimum_number_of_chunks: int,
) -> list[RetrievedChunk]:
    """Applique le seuil, le minimum de résultats et le tri de pertinence.

    Args:
        chunks: Résultats bruts retournés par le repository.
        minimum_similarity: Similarité minimale normalement requise.
        minimum_number_of_chunks: Nombre minimal à conserver si disponible.

    Returns:
        Résultats triés par similarité décroissante.
    """
    sorted_chunks = sorted(chunks, key=lambda chunk: chunk.similarity, reverse=True)
    selected = [
        chunk for chunk in sorted_chunks if chunk.similarity >= minimum_similarity
    ]
    if len(selected) < minimum_number_of_chunks:
        return sorted_chunks[:minimum_number_of_chunks]
    return selected


def format_retrieved_chunk(chunk: RetrievedChunk) -> ChunkModelBase:
    """Convertit un résultat métier en schéma de réponse public.

    Args:
        chunk: Chunk indépendant du format de réponse ChromaDB.

    Returns:
        DTO exposé à l'orchestrator.

    Raises:
        RetrievalFormatException: Si les valeurs du chunk sont invalides.
    """
    try:
        metadata = VectorMetadataBase(**chunk.metadata.to_storage_dict())
        return ChunkModelBase(
            id=(
                f"{chunk.metadata.title} | {chunk.metadata.path} | "
                f"{chunk.metadata.chunk_index}"
            ),
            document=chunk.document,
            metadata=metadata,
            similarity=round(chunk.similarity, 3),
        )
    except (TypeError, ValueError) as exception:
        raise RetrievalFormatException(
            internal_details={"operation": "format_retrieved_chunk"},
        ) from exception
