from decimal import Decimal
from typing import Self

import pytest
from app.core.exceptions import DependencyResponseError
from app.schemas.llm_response_schema import ApiLlmUsage
from app.services import ask_question_service
from app.services.ask_question_service import (
    _extract_api_response_text,
    _record_llm_usage,
    _validate_api_llm_response,
    calculate_cost,
    design_source,
)


class RecordingMetric:
    def __init__(self, name: str, calls: list[tuple[str, float]]) -> None:
        self.name = name
        self.calls = calls

    def labels(self, **labels: str) -> Self:
        return self

    def inc(self, value: float) -> None:
        self.calls.append((self.name, value))


def test_design_source_counts_documents_sorted_by_occurrence() -> None:
    chunks = [
        {"metadata": {"title": "Doc A"}},
        {"metadata": {"title": "Doc B"}},
        {"metadata": {"title": "Doc A"}},
    ]

    assert design_source(chunks) == {"Doc A": 2, "Doc B": 1}


def test_calculate_cost_uses_preloaded_model_pricing() -> None:
    cost = calculate_cost(
        usage=ApiLlmUsage(
            input_tokens=1_000_000,
            output_tokens=500_000,
            total_tokens=1_500_000,
        ),
        input_price=Decimal("2.0"),
        output_price=Decimal("6.0"),
    )

    assert cost == 5.0


def test_extract_api_response_text_finds_typed_message_without_fixed_position() -> None:
    response = _validate_api_llm_response(
        {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "answer"}],
                },
                {"type": "function_call", "content": []},
            ],
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        }
    )

    assert _extract_api_response_text(response) == "answer"


def test_extract_api_response_text_rejects_missing_text() -> None:
    response = _validate_api_llm_response(
        {
            "output": [{"type": "message", "content": []}],
            "usage": {"input_tokens": 1, "output_tokens": 0, "total_tokens": 1},
        }
    )

    try:
        _extract_api_response_text(response)
    except DependencyResponseError as exception:
        assert exception.details == {"dependency": "llm", "operation": "api_llm"}
    else:
        raise AssertionError("A response without generated text must be rejected")


def test_record_llm_usage_records_cost_only_in_eur_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float]] = []
    response = _validate_api_llm_response(
        {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "answer"}],
                }
            ],
            "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        }
    )
    monkeypatch.setattr(
        ask_question_service,
        "orchestrator_tokens_total",
        RecordingMetric("orchestrator_tokens", calls),
    )
    monkeypatch.setattr(
        ask_question_service,
        "orchestrator_cost_total",
        RecordingMetric("orchestrator_cost_eur", calls),
    )
    monkeypatch.setattr(
        ask_question_service,
        "rag_tokens_total",
        RecordingMetric("rag_tokens", calls),
    )
    monkeypatch.setattr(
        ask_question_service,
        "rag_cost_eur_total",
        RecordingMetric("rag_cost_eur", calls),
    )

    _record_llm_usage("openai", "model", response, 0.25)

    assert ("orchestrator_cost_eur", 0.25) in calls
    assert ("rag_cost_eur", 0.25) in calls
    assert not hasattr(ask_question_service, "rag_cost_usd_total")
