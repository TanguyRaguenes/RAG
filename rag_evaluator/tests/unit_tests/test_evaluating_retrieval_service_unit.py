from app.services.evaluating_retrieval_service import (
    evaluate_retrieval,
    extract_retrieved_texts,
)


def test_extract_retrieved_texts_reads_document_from_dict_chunks() -> None:
    chunks = [
        {"document": "chunk A"},
        {"document": ""},
        {"metadata": {"title": "sans document"}},
        "chunk B",
    ]

    assert extract_retrieved_texts(chunks) == ["chunk A", "chunk B"]


def test_evaluate_retrieval_returns_zero_scores_without_keywords() -> None:
    result = evaluate_retrieval(keywords=[], retrieved_chunks=["chunk"], k=5)

    assert result.mrr == 0
    assert result.ndcg == 0
    assert result.recall == 0
    assert result.precision == 0


def test_evaluate_retrieval_calculates_scores_from_extracted_texts() -> None:
    result = evaluate_retrieval(
        keywords=["kelio"],
        retrieved_chunks=[{"document": "usage kelio"}, {"document": "bruit"}],
        k=2,
    )

    assert result.mrr == 1.0
    assert result.ndcg == 1.0
    assert result.recall == 1.0
    assert result.precision == 0.5
