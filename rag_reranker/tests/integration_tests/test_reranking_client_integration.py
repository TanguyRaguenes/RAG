import os

import pytest

from app.core.config import load_config
from app.dal.clients.reranking_client import score_chunks


@pytest.mark.asyncio
async def test_score_chunks_returns_scores_with_local_tei():
    if os.getenv("RAG_RERANKER_RUN_INTEGRATION") != "1":
        pytest.skip("Set RAG_RERANKER_RUN_INTEGRATION=1 with TEI running locally")

    config = load_config()
    config["reranking"]["url"] = "http://localhost:8081/rerank"

    scores = await score_chunks(
        "Comment configurer Docker ?",
        [
            {
                "document": "Docker Compose permet de déclarer des services.",
                "metadata": {"title": "Docker"},
            }
        ],
        config=config,
    )

    assert 0 in scores
    assert 0.0 <= scores[0] <= 1.0
