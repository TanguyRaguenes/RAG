from typing import Any, List

from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services.calculating_metrics import (
    calculate_mrr,
    calculate_ndcg,
    calculate_keyword_coverage,
)


def extract_retrieved_texts(raw_chunks: list[Any]) -> List[str]:
    """
    Tolère différents formats de chunks.
    - chunk peut être dict avec "document" ou "text"
    - sinon on fait str(chunk)
    """
    out: list[str] = []
    for c in raw_chunks:
        if isinstance(c, dict):
            txt = c.get("document") or c.get("text") or ""
            if txt:
                out.append(str(txt))
        else:
            out.append(str(c))
    return out


def evaluate_retrieval(keywords: List[str], raw_chunks: list[Any], k: int = 5) -> RetrievalEvaluationBase:

    retrieved_texts = extract_retrieved_texts(raw_chunks)

    if not keywords:
        return RetrievalEvaluationBase(
            mrr=0, ndcg=0, keywords_found=0, total_keywords=0, keyword_coverage=0
        )

    mrr_scores = [calculate_mrr(kw, retrieved_texts) for kw in keywords]
    ndcg_scores = [calculate_ndcg(kw, retrieved_texts, k) for kw in keywords]

    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    found, total, coverage = calculate_keyword_coverage(keywords, retrieved_texts)

    return RetrievalEvaluationBase(
        mrr=round(avg_mrr, 4),
        ndcg=round(avg_ndcg, 4),
        keywords_found=found,
        total_keywords=total,
        keyword_coverage=round(coverage, 2),
    )
