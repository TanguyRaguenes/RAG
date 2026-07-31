from pathlib import PurePosixPath
from typing import Any

from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services.calculating_metrics_service import (
    calculate_mrr,
    calculate_ndcg,
    calculate_precision,
    calculate_recall,
)


def extract_retrieved_texts(raw_chunks: list[Any]) -> list[str]:
    """Extrait le contenu textuel des chunks récupérés pour calculer les métriques.

    Args:
        raw_chunks: Chunks bruts retournés par l'orchestrator avant extraction du texte utile.

    Returns:
        Textes de chunks exploitables pour les métriques de retrieval.
    """
    retrieved_texts: list[str] = []
    for chunk in raw_chunks:
        if isinstance(chunk, dict):
            document = chunk.get("document")
            if document:
                retrieved_texts.append(str(document))
        else:
            retrieved_texts.append(str(chunk))

    return retrieved_texts


def evaluate_retrieval(
    keywords: list[str],
    retrieved_chunks: list[Any],
    k: int,
    expected_sources: list[str] | None = None,
) -> RetrievalEvaluationBase:
    """Calcule les métriques de retrieval pour une question du dataset.

    Args:
        keywords: Mots-clés attendus pour mesurer la récupération documentaire.
        retrieved_chunks: Chunks retournés par le retriever ou l'orchestrator.
        k: Nombre de premiers résultats pris en compte pour la métrique.
        expected_sources: Sources documentaires attendues pour le KPI source hit at 5.

    Returns:
        Scores MRR, nDCG, recall et precision calculés pour la question.
    """
    retrieved_texts = extract_retrieved_texts(retrieved_chunks)
    source_hit_at_5 = calculate_source_hit_at_k(expected_sources, retrieved_chunks, k=5)

    if not keywords or not retrieved_chunks:
        return RetrievalEvaluationBase(
            mrr=0,
            ndcg=0,
            recall=0,
            precision=0,
            source_hit_at_5=source_hit_at_5,
        )

    mrr_score: float = calculate_mrr(keywords, retrieved_texts)
    ndcg_score: float = calculate_ndcg(keywords, retrieved_texts, k)
    recall_score: float = calculate_recall(keywords, retrieved_texts)
    precision_score: float = calculate_precision(keywords, retrieved_texts, k)

    return RetrievalEvaluationBase(
        mrr=mrr_score,
        ndcg=ndcg_score,
        recall=recall_score,
        precision=precision_score,
        source_hit_at_5=source_hit_at_5,
    )


def calculate_source_hit_at_k(
    expected_sources: list[str] | None,
    retrieved_chunks: list[Any],
    k: int,
) -> float:
    """Indique si au moins une source attendue apparaît dans les k premiers chunks.

    Args:
        expected_sources: Fichiers Markdown attendus pour la question.
        retrieved_chunks: Chunks retournés par le retriever ou l'orchestrator.
        k: Nombre de premiers chunks inspectés.

    Returns:
        `1.0` si une source attendue est retrouvée, sinon `0.0`.
    """
    if not expected_sources or not retrieved_chunks:
        return 0.0

    normalized_expected = {normalize_source_name(source) for source in expected_sources}

    for chunk in retrieved_chunks[:k]:
        if not isinstance(chunk, dict):
            continue
        metadata = chunk.get("metadata") or {}
        chunk_sources = [
            metadata.get("path"),
            metadata.get("source"),
            metadata.get("source_file"),
            metadata.get("title"),
        ]
        normalized_chunk_sources = {
            normalize_source_name(source)
            for source in chunk_sources
            if isinstance(source, str) and source
        }

        if normalized_expected.intersection(normalized_chunk_sources):
            return 1.0

    return 0.0


def normalize_source_name(source: str) -> str:
    """Normalise un nom de source pour comparer chemins et noms de fichiers.

    Args:
        source: Chemin ou nom de fichier documentaire.

    Returns:
        Nom de fichier normalisé en minuscules.
    """
    return PurePosixPath(source.replace("\\", "/")).name.lower()
