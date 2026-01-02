import math
from typing import List


def calculate_mrr(keyword: str, retrieved_texts: List[str]) -> float:
    keyword_lower = keyword.lower()
    for rank, text in enumerate(retrieved_texts, start=1):
        if keyword_lower in text.lower():
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: List[int], k: int) -> float:
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)
    return dcg


def calculate_ndcg(keyword: str, retrieved_texts: List[str], k: int = 5) -> float:
    keyword_lower = keyword.lower()
    relevances = [1 if keyword_lower in t.lower() else 0 for t in retrieved_texts[:k]]
    dcg = calculate_dcg(relevances, k)
    idcg = calculate_dcg(sorted(relevances, reverse=True), k)
    return (dcg / idcg) if idcg > 0 else 0.0


def calculate_keyword_coverage(keywords: List[str], retrieved_texts: List[str]) -> tuple[int, int, float]:
    if not keywords:
        return (0, 0, 0.0)
    mrr_scores = [calculate_mrr(kw, retrieved_texts) for kw in keywords]
    found = sum(1 for s in mrr_scores if s > 0)
    total = len(keywords)
    coverage = (found / total) * 100
    return (found, total, coverage)
