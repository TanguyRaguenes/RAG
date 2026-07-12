import pytest

from app.api.routers import evaluate_router
from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase


@pytest.mark.asyncio
async def test_ask_question_route_sets_total_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_evaluate_rag(config):
        assert config == {"config": True}
        return EvaluatorResponseBase(
            average_retrieval=RetrievalEvaluationBase(
                mrr=1, ndcg=1, recall=1, precision=1
            ),
            average_answer_quality=AnswerEvaluationBase(
                feedback="ok", accuracy=4, completeness=4, relevance=4
            ),
            total_duration="ignored",
            total_questions=2,
        )

    monkeypatch.setattr(evaluate_router, "evaluate_rag", fake_evaluate_rag)
    monkeypatch.setattr(
        evaluate_router.time, "perf_counter", iter([1.0, 62.0]).__next__
    )

    response = await evaluate_router.ask_question_route({"config": True})

    assert response.total_duration == "01:01"
    assert response.total_questions == 2
    assert response.average_retrieval.mrr == 1
