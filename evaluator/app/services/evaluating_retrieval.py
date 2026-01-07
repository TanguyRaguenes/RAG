from typing import Any, List

from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services.calculating_metrics import (
    calculate_mrr,
    calculate_ndcg,
    calculate_recall,
    calculate_precision
)


def extract_retrieved_texts(raw_chunks: list[Any]) -> List[str]:

    out: list[str] = []
    for chunk in raw_chunks:
        if isinstance(chunk, dict):
            txt = chunk.get("document")
            if txt:
                out.append(str(txt))
        else:
            out.append(str(chunk))
    return out


def evaluate_retrieval(keywords: List[str], retrieved_chunks: list[Any], k: int) -> RetrievalEvaluationBase:

    retrieved_texts = extract_retrieved_texts(retrieved_chunks)

    if not keywords or not retrieved_chunks:
        return RetrievalEvaluationBase(
            mrr=0, ndcg=0, recall=0,precision=0
        )

    mrr_score:float = calculate_mrr(keywords, retrieved_texts)
    ndcg_score:float = calculate_ndcg(keywords, retrieved_texts, k)

    recall_score:float = calculate_recall(keywords, retrieved_texts)
    precision_score:float = calculate_precision(keywords,retrieved_texts,k)

    return RetrievalEvaluationBase(
        mrr=mrr_score,
        ndcg=ndcg_score,
        recall=recall_score,
        precision=precision_score
    )
