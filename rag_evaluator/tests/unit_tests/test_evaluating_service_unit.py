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
from app.services import evaluating_service


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


@pytest.mark.asyncio
async def test_evaluate_rag_averages_retrieval_and_valid_answer_judgements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        evaluating_service,
        "load_dataset",
        lambda: [
            {"question": "Q1", "reference_answer": "R1", "keywords": ["a"]},
            {"question": "Q2", "reference_answer": "R2", "keywords": ["b"]},
        ],
    )

    async def fake_ask_question(question: str):
        return {
            "llm_response": f"answer {question}",
            "retrieved_chunks": [{"document": "doc", "metadata": {"title": "T"}, "similarity": 0.9}],
            "retrieved_documents": {"T": 1},
            "model": "model",
            "generated_prompt": [],
            "duration": "00:01",
        }

    def fake_evaluate_retrieval(keywords, retrieved_chunks, k):
        return RetrievalEvaluationBase(mrr=1, ndcg=0.5, recall=0.25, precision=0.75)

    async def fake_evaluate_answer(**kwargs):
        return AnswerEvaluationBase(feedback="ok", accuracy=4, completeness=3, relevance=5)

    monkeypatch.setattr(evaluating_service, "ask_question", fake_ask_question)
    monkeypatch.setattr(evaluating_service, "evaluate_retrieval", fake_evaluate_retrieval)
    monkeypatch.setattr(evaluating_service, "evaluate_answer", fake_evaluate_answer)

    result = await evaluating_service.evaluate_rag({})

    assert result.total_questions == 2
    assert result.average_retrieval.mrr == 1
    assert result.average_answer_quality.accuracy == 4


@pytest.mark.asyncio
async def test_evaluate_rag_continues_when_orchestrator_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluating_service, "load_dataset", lambda: [{"question": "Q", "reference_answer": "R"}])

    async def failing_ask_question(question: str):
        raise RuntimeError("rag down")

    retrieval_calls = []

    def fake_evaluate_retrieval(keywords, retrieved_chunks, k):
        retrieval_calls.append(retrieved_chunks)
        return RetrievalEvaluationBase(mrr=0, ndcg=0, recall=0, precision=0)

    async def failing_evaluate_answer(**kwargs):
        raise RuntimeError("judge down")

    monkeypatch.setattr(evaluating_service, "ask_question", failing_ask_question)
    monkeypatch.setattr(evaluating_service, "evaluate_retrieval", fake_evaluate_retrieval)
    monkeypatch.setattr(evaluating_service, "evaluate_answer", failing_evaluate_answer)

    result = await evaluating_service.evaluate_rag({})

    assert retrieval_calls == [[]]
    assert result.average_answer_quality.accuracy == 0
