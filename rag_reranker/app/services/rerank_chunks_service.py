from typing import Any

from app.dal.clients.reranking_client import score_chunks


async def rerank_chunks(
    question: str,
    chunks: list[dict[str, Any]],
    config: dict,
) -> list[dict[str, Any]]:
    """Réordonne les chunks candidats selon leur pertinence pour la question.

    Args:
        question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
        chunks: Chunks documentaires manipulés par le pipeline RAG.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Chunks enrichis avec `rerank_score`, triés et limités par la configuration.
    """
    if not chunks:
        return []

    top_k: int = config["reranking"].get("top_k", len(chunks))
    if top_k <= 0:
        return []

    scores = await score_chunks(question, chunks, config)

    scored_chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        score = scores.get(index, 0.0)
        scored_chunk = dict(chunk)
        scored_chunk["rerank_score"] = score
        scored_chunks.append(scored_chunk)

    return sorted(
        scored_chunks,
        key=lambda chunk: (chunk["rerank_score"], chunk.get("similarity", 0.0)),
        reverse=True,
    )[:top_k]
