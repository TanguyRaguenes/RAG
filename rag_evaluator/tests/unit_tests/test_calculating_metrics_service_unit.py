from app.services.calculating_metrics_service import (
    calculate_dcg,
    calculate_mrr,
    calculate_ndcg,
    calculate_precision,
    calculate_recall,
    contains_keyword,
    normalize_texts,
)


def test_calculate_mrr_averages_first_matching_rank_per_keyword() -> None:
    result = calculate_mrr(
        keywords=["Kelio", "Moffi", "Absence"],
        retrieved_chunks=["Moffi reservation", "Kelio badgeage"],
    )

    assert result == (0.5 + 1.0 + 0.0) / 3


def test_calculate_ndcg_rewards_relevant_chunks_at_top() -> None:
    result = calculate_ndcg(
        keywords=["kelio", "moffi"],
        retrieved_chunks=["kelio badgeage", "bruit", "moffi reservation"],
        k=3,
    )

    assert round(result, 3) == 0.92


def test_calculate_recall_counts_keywords_found_anywhere() -> None:
    result = calculate_recall(
        keywords=["kelio", "moffi", "cleemy"],
        retrieved_chunks=["kelio et moffi sont cités"],
    )

    assert result == 2 / 3


def test_calculate_precision_counts_relevant_chunks_in_top_k() -> None:
    result = calculate_precision(
        keywords=["kelio"],
        retrieved_chunks=["kelio badgeage", "bruit", "kelio absences"],
        k=2,
    )

    assert result == 0.5


def test_calculate_dcg_applies_log_discount() -> None:
    assert round(calculate_dcg([1, 0, 1]), 3) == 1.5


def test_text_helpers_normalize_and_match_keywords() -> None:
    assert normalize_texts(["Kelio", "MOFFI"]) == ["kelio", "moffi"]
    assert contains_keyword("usage kelio", ["kelio"])
