from decimal import Decimal
from typing import Any

import pytest

from app.services import ask_question_service
from app.services.ask_question_service import calculate_cost, design_source


def test_design_source_counts_documents_sorted_by_occurrence() -> None:
    chunks = [
        {"metadata": {"title": "Doc A"}},
        {"metadata": {"title": "Doc B"}},
        {"metadata": {"title": "Doc A"}},
    ]

    assert design_source(chunks) == {"Doc A": 2, "Doc B": 1}


@pytest.mark.asyncio
async def test_calculate_cost_uses_model_pricing(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUsageRepository:
        def __init__(self, db_pool: Any):
            self.db_pool = db_pool

        async def get_active_model_pricing(
            self,
            *,
            provider: str,
            model_name: str,
        ) -> tuple[Decimal, Decimal]:
            assert provider == "openai"
            assert model_name == "gpt-test"
            return Decimal("2.0"), Decimal("6.0")

    monkeypatch.setattr(ask_question_service, "UsageRepository", FakeUsageRepository)

    cost = await calculate_cost(
        llm_response={
            "usage": {
                "input_tokens": 1_000_000,
                "output_tokens": 500_000,
            }
        },
        db_pool=object(),
        provider="openai",
        model="gpt-test",
    )

    assert cost == 5.0
