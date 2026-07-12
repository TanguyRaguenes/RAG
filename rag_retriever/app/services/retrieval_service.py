from typing import Any

from app.core.exceptions import RetrievalFormatException, VectorStoreException
from app.core.metrics import retriever_chunks_total
from app.schemas.retrieve_chunks_response_schema import (
    ChunkModelBase,
    RetrievedChunksModelBase,
)


def retrieve_chunks(
    config: dict[str, Any],
    collection,
    embeded_question: list[float],
    vector_store_repository,
) -> RetrievedChunksModelBase:
    """Recherche et formate les chunks pertinents pour une question vectorisée.

    Args:
        config: Configuration contenant `top_k`, `minimum_similarity` et `minimum_number_of_chunks`.
        collection: Collection ChromaDB à interroger.
        embeded_question: Embedding de la question utilisateur.
        vector_store_repository: Repository vectoriel chargé de l'appel ChromaDB.

    Returns:
        Chunks filtrés et formatés pour l'orchestrator.

    Raises:
        VectorStoreException: Si ChromaDB échoue pendant la recherche.
        RetrievalFormatException: Si un chunk retourné est incomplet ou mal formé.
        KeyError: Si la configuration ne contient pas les clés attendues.
    """
    top_k: int = config["retriever"]["top_k"]
    minimum_similarity: float = config["retriever"]["minimum_similarity"]
    minimum_number_of_chunks: int = config["retriever"]["minimum_number_of_chunks"]

    try:
        retrieved_chunks: list[dict[str, Any]] = (
            vector_store_repository.retrieve_chunks_filtered(
                collection,
                embeded_question,
                top_k,
                minimum_similarity,
                minimum_number_of_chunks,
            )
        )
    except Exception as exception:
        if isinstance(exception, VectorStoreException):
            raise
        raise VectorStoreException(
            message="Erreur lors de la recherche de chunks",
            details={"operation": "retrieve_chunks"},
        ) from exception

    retriever_chunks_total.labels(operation="retrieve_chunks").inc(
        len(retrieved_chunks)
    )

    return RetrievedChunksModelBase(
        chunks=[format_retrieved_chunk(chunk) for chunk in retrieved_chunks]
    )


def retrieve_document_chunks(
    collection,
    paths: list[str],
    vector_store_repository,
) -> RetrievedChunksModelBase:
    """Récupère tous les chunks associés à une liste de chemins documentaires.

    Args:
        collection: Collection ChromaDB à interroger.
        paths: Chemins documentaires à récupérer.
        vector_store_repository: Repository vectoriel chargé de l'appel ChromaDB.

    Returns:
        Chunks documentaires formatés pour l'orchestrator.

    Raises:
        VectorStoreException: Si ChromaDB échoue pendant la récupération.
        RetrievalFormatException: Si un chunk retourné est incomplet ou mal formé.
    """
    try:
        document_chunks = vector_store_repository.retrieve_document_chunks_by_paths(
            collection,
            paths,
        )
    except Exception as exception:
        if isinstance(exception, VectorStoreException):
            raise
        raise VectorStoreException(
            message="Erreur lors de la récupération des chunks documentaires",
            details={"operation": "retrieve_document_chunks"},
        ) from exception

    retriever_chunks_total.labels(operation="retrieve_document_chunks").inc(
        len(document_chunks)
    )

    return RetrievedChunksModelBase(
        chunks=[format_retrieved_chunk(chunk) for chunk in document_chunks]
    )


def format_retrieved_chunk(chunk: dict[str, Any]) -> ChunkModelBase:
    """Convertit un chunk brut en schéma de réponse.

    Args:
        chunk: Chunk brut contenant document, métadonnées et similarité.

    Returns:
        Chunk Pydantic prêt à être renvoyé par l'API.

    Raises:
        RetrievalFormatException: Si le chunk ne contient pas les champs requis.
    """
    try:
        metadata = chunk["metadata"]

        return ChunkModelBase(
            id=_build_chunk_id(metadata),
            document=chunk["document"],
            metadata=metadata,
            similarity=round(chunk["similarity"], 3),
        )
    except TypeError as exception:
        raise RetrievalFormatException(
            message="Chunk récupéré mal formé",
            details={"missing_or_invalid_field": str(exception)},
        ) from exception


def _build_chunk_id(metadata: dict[str, Any]) -> str:
    """Construit l'identifiant lisible d'un chunk.

    Args:
        metadata: Métadonnées contenant `title`, `path` et `chunk_index`.

    Returns:
        Identifiant lisible du chunk.

    Raises:
        KeyError: Si une métadonnée obligatoire manque.
    """
    return f"{metadata['title']} | {metadata['path']} | {metadata['chunk_index']}"
