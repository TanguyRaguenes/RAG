import pytest

from app.api.routers import evaluate_router
from app.core.config import EvaluatorConfig
from app.schemas.answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase


@pytest.mark.asyncio
async def test_ask_question_route_sets_total_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_config = EvaluatorConfig.model_validate(
        {
            "llm": {
                "provider": "ollama",
                "url_provider": "http://ollama",
                "model": "judge",
                "temperature": 0.1,
                "num_ctx": 1024,
                "max_output_token": 128,
                "timeout_seconds": 10,
            },
            "evaluation_method": {"use_api_openai": False},
        }
    )

    async def fake_evaluate_rag(
        *, config: EvaluatorConfig, access_token: str
    ) -> EvaluatorResponseBase:
        assert config is expected_config
        assert access_token == "opaque-token"
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

    response = await evaluate_router.ask_question_route(expected_config, "opaque-token")

    assert response.total_duration == "01:01"
    assert response.total_questions == 2
    assert response.average_retrieval.mrr == 1
