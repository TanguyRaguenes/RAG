import json

import pytest

from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services.evaluating_service import (
    add_quality_score,
    add_retrieval_score,
    build_empty_evaluation_response,
    build_quality_accumulator,
    build_retrieval_accumulator,
    calculate_average_quality,
    calculate_average_retrieval,
    load_dataset,
)


def test_load_dataset_reads_list_from_configured_path(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset = [{"question": "Q", "reference_answer": "R"}]
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    monkeypatch.setenv("DATASET_PATH", str(dataset_path))

    assert load_dataset() == dataset


def test_load_dataset_requires_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATASET_PATH", raising=False)

    with pytest.raises(ValueError):
        load_dataset()


def test_build_empty_evaluation_response_returns_zero_scores() -> None:
    response = build_empty_evaluation_response()

    assert response.total_questions == 0
    assert response.average_retrieval.mrr == 0.0
    assert response.average_answer_quality.feedback == "Aucune évaluation"


def test_retrieval_accumulator_and_average() -> None:
    accumulator = build_retrieval_accumulator()

    add_retrieval_score(
        accumulator,
        RetrievalEvaluationBase(mrr=1, ndcg=0.5, recall=0.25, precision=0.75),
    )
    add_retrieval_score(
        accumulator,
        RetrievalEvaluationBase(mrr=0, ndcg=0.5, recall=0.75, precision=0.25),
    )

    average = calculate_average_retrieval(accumulator, total_questions=2)

    assert average.mrr == 0.5
    assert average.ndcg == 0.5
    assert average.recall == 0.5
    assert average.precision == 0.5


def test_quality_accumulator_and_average() -> None:
    accumulator = build_quality_accumulator()

    add_quality_score(
        accumulator,
        AnswerEvaluationBase(feedback="ok", accuracy=4, completeness=3, relevance=5),
    )
    add_quality_score(
        accumulator,
        AnswerEvaluationBase(feedback="ok", accuracy=2, completeness=5, relevance=3),
    )

    average = calculate_average_quality(accumulator, valid_judgements=2)

    assert average.accuracy == 3
    assert average.completeness == 4
    assert average.relevance == 4


def test_quality_average_uses_safe_divisor_without_judgements() -> None:
    average = calculate_average_quality(build_quality_accumulator(), valid_judgements=0)

    assert average.accuracy == 0
    assert average.completeness == 0
    assert average.relevance == 0
