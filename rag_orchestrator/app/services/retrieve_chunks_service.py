from typing import Any, Literal

from opentelemetry import trace

from app.dal.clients.embedder_client import embed
from app.dal.clients.reranker_client import rerank_chunks as rerank_chunks_client
from app.dal.clients.retriever_client import retrieve_chunks as retrieve_chunks_client
from app.dal.clients.retriever_client import (
    retrieve_document_chunks as retrieve_document_chunks_client,
)
from app.schemas.retrieve_chunks_response_schema import (
    RetrieveChunksResponseBase,
)

tracer = trace.get_tracer(__name__)


async def retrieve_chunks(
    question: str,
    config: dict,
    collection_profile: Literal["default", "evaluation"] = "default",
) -> RetrieveChunksResponseBase:
    """Récupère les chunks pertinents pour une question.

    Args:
        question: Question utilisateur, non loggée pour éviter l'exposition de contenu.
        config: Configuration applicative du pipeline RAG.
        collection_profile: Profil fixe de collection à interroger.

    Returns:
        Réponse contenant les chunks récupérés et éventuellement étendus au document complet.

    Raises:
        OrchestratorContainerCustomException: Si embedder, retriever ou reranker échoue.
        KeyError: Si une clé de configuration attendue est absente.
    """
    with tracer.start_as_current_span("orchestrator.retrieve_chunks_service"):
        selected_chunks, _ = await retrieve_and_rerank_chunks(
            question, config, collection_profile
        )

        return RetrieveChunksResponseBase(
            retrieved_chunks=selected_chunks,
        )


async def retrieve_and_rerank_chunks(
    question: str,
    config: dict,
    collection_profile: Literal["default", "evaluation"] = "default",
) -> tuple[list[dict[str, Any]], bool]:
    """Exécute embedding, retrieval, reranking optionnel et extension documentaire.

    Args:
        question: Question utilisateur à traiter.
        config: Configuration du reranking et de l'extension documentaire.
        collection_profile: Profil fixe de collection à interroger.

    Returns:
        Chunks sélectionnés et état actuel du chunking de l'embedder.

    Raises:
        OrchestratorContainerCustomException: Si un client interservice échoue.
        IndexError: Si le service embedder ne retourne aucun embedding.
        KeyError: Si une clé de configuration attendue est absente.
    """
    with tracer.start_as_current_span("orchestrator.retrieve_and_rerank") as span:
        embeddings, chunking_enabled = await embed([question])
        embeded_question: list[float] = embeddings[0]

        retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks_client(
            embeded_question,
            collection_profile,
        )
        span.set_attribute("retrieval.chunk_count", len(retrieved_chunks))

        selected_chunks = retrieved_chunks
        use_reranker: bool = config["retrieval"]["use_reranker"]
        span.set_attribute("reranking.enabled", use_reranker)
        if use_reranker:
            selected_chunks = await rerank_chunks_client(
                question,
                retrieved_chunks,
            )
            span.set_attribute("reranking.chunk_count", len(selected_chunks))

        if not config["retrieval"]["fetch_all_chunks_by_path"]:
            return selected_chunks, chunking_enabled

        paths = extract_unique_paths(selected_chunks)
        document_chunks: list[dict[str, Any]] = await retrieve_document_chunks_client(
            paths,
            collection_profile,
        )
        span.set_attribute("retrieval.document_path_count", len(paths))
        span.set_attribute("retrieval.document_chunk_count", len(document_chunks))

        return document_chunks, chunking_enabled


def extract_unique_paths(chunks: list[dict[str, Any]]) -> list[str]:
    """Extrait les chemins de documents uniques dans l'ordre des chunks.

    Args:
        chunks: Chunks contenant éventuellement `metadata.path`.

    Returns:
        Liste de chemins uniques, sans valeur vide.
    """
    paths: list[str] = []
    seen_paths: set[str] = set()

    for chunk in chunks:
        path = chunk.get("metadata", {}).get("path")
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        paths.append(path)

    return paths
