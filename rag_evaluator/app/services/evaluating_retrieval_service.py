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
    keywords: list[str], retrieved_chunks: list[Any], k: int
) -> RetrievalEvaluationBase:
    """Calcule les métriques de retrieval pour une question du dataset.

    Args:
        keywords: Mots-clés attendus pour mesurer la récupération documentaire.
        retrieved_chunks: Chunks retournés par le retriever ou l'orchestrator.
        k: Nombre de premiers résultats pris en compte pour la métrique.

    Returns:
        Scores MRR, nDCG, recall et precision calculés pour la question.
    """
    retrieved_texts = extract_retrieved_texts(retrieved_chunks)

    if not keywords or not retrieved_chunks:
        return RetrievalEvaluationBase(mrr=0, ndcg=0, recall=0, precision=0)

    mrr_score: float = calculate_mrr(keywords, retrieved_texts)
    ndcg_score: float = calculate_ndcg(keywords, retrieved_texts, k)
    recall_score: float = calculate_recall(keywords, retrieved_texts)
    precision_score: float = calculate_precision(keywords, retrieved_texts, k)

    return RetrievalEvaluationBase(
        mrr=mrr_score,
        ndcg=ndcg_score,
        recall=recall_score,
        precision=precision_score,
    )
