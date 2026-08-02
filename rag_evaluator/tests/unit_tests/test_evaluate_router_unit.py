import pytest

from app.api.routers import evaluate_router
from app.core.config import EvaluatorConfig
from app.schemas.answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.evaluate_request_schema import EvaluateRequest
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase


@pytest.mark.asyncio
async def test_ask_question_route_sets_total_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_config = EvaluatorConfig.model_validate(
        {
            "rag_provider": "api",
            "judge_provider": "local",
            "llm": {
                "common": {
                    "temperature": 0.1,
                    "timeout_seconds": 10,
                    "stream": False,
                },
                "local": {
                    "provider": "Ollama",
                    "endpoint": "http://ollama/v1/chat/completions",
                    "model": "judge",
                    "context_window_tokens": 1024,
                    "max_output_tokens": 128,
                    "max_prompt_chars": 2000,
                },
                "api": {
                    "provider": "OpenAi",
                    "endpoint": "https://api.openai.com/v1/responses",
                    "model": "judge-api",
                    "max_output_tokens": 128,
                    "max_prompt_chars": 4000,
                },
            },
        }
    )

    async def fake_evaluate_rag(
        *, config: EvaluatorConfig, access_token: str, question_limit: int | None
    ) -> EvaluatorResponseBase:
        assert config is expected_config
        assert access_token == "opaque-token"
        assert question_limit == 12
        return EvaluatorResponseBase(
            average_retrieval=RetrievalEvaluationBase(
                mrr=1, ndcg=1, recall=1, precision=1
            ),
            average_answer_quality=AnswerEvaluationBase(
                feedback="ok",
                accuracy=4,
                completeness=4,
                relevance=4,
                faithfulness=4,
                safe_refusal=5,
            ),
            total_duration="ignored",
            total_questions=2,
        )

    monkeypatch.setattr(evaluate_router, "evaluate_rag", fake_evaluate_rag)
    monkeypatch.setattr(
        evaluate_router.time, "perf_counter", iter([1.0, 62.0]).__next__
    )

    response = await evaluate_router.ask_question_route(
        expected_config, "opaque-token", EvaluateRequest(question_limit=12)
    )

    assert response.total_duration == "01:01"
    assert response.total_questions == 2
    assert response.average_retrieval.mrr == 1
