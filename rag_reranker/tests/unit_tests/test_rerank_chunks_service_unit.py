import pytest

from app.services import rerank_chunks_service


def _chunks() -> list[dict]:
    return [
        {
            "id": "chunk-1",
            "document": "first",
            "metadata": {"title": "A"},
            "similarity": 0.8,
        },
        {
            "id": "chunk-2",
            "document": "second",
            "metadata": {"title": "B"},
            "similarity": 0.9,
        },
        {
            "id": "chunk-3",
            "document": "third",
            "metadata": {"title": "C"},
            "similarity": 0.7,
        },
    ]


@pytest.mark.asyncio
async def test_rerank_chunks_orders_by_rerank_score_and_applies_top_k(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_score_chunks(
        question: str, chunks: list[dict], config: dict
    ) -> dict[int, float]:
        assert question == "Question"
        assert len(chunks) == 3
        assert config == {"reranking": {"top_k": 2}}
        return {0: 0.2, 1: 0.95, 2: 0.5}

    monkeypatch.setattr(rerank_chunks_service, "score_chunks", fake_score_chunks)

    response = await rerank_chunks_service.rerank_chunks(
        "Question",
        _chunks(),
        {"reranking": {"top_k": 2}},
    )

    assert [chunk["id"] for chunk in response] == ["chunk-2", "chunk-3"]
    assert response[0]["rerank_score"] == 0.95


@pytest.mark.asyncio
async def test_rerank_chunks_returns_empty_list_when_chunks_are_empty() -> None:
    response = await rerank_chunks_service.rerank_chunks(
        "Question",
        [],
        {"reranking": {"top_k": 2}},
    )

    assert response == []


@pytest.mark.asyncio
async def test_rerank_chunks_uses_similarity_when_scores_are_equal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_score_chunks(
        question: str, chunks: list[dict], config: dict
    ) -> dict[int, float]:
        return {0: 0.5, 1: 0.5, 2: 0.5}

    monkeypatch.setattr(rerank_chunks_service, "score_chunks", fake_score_chunks)

    response = await rerank_chunks_service.rerank_chunks(
        "Question",
        _chunks(),
        {"reranking": {"top_k": 3}},
    )

    assert [chunk["id"] for chunk in response] == ["chunk-2", "chunk-1", "chunk-3"]
