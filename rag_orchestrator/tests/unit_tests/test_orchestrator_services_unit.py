import pytest

from app.services import ask_question_service, retrieve_chunks_service
from app.services.auth_service import AuthService
from app.services.user_identity_service import (
    build_user_id_from_email,
    build_user_id_from_identifier,
)


def _config() -> dict:
    return {
        "retrieval": {"fetch_all_chunks_by_path": True},
        "llm": {
            "common": {"timeout_seconds": 30, "temperature": 0.2, "stream": False},
            "local": {
                "endpoint": "http://ollama/v1/chat/completions",
                "model": "local-model",
                "max_output_tokens": 128,
                "context_window_tokens": 4096,
                "max_prompt_chars": 1000,
            },
            "api": {
                "provider": "openai",
                "endpoint": "http://api/v1/responses",
                "model": "api-model",
                "max_output_tokens": 128,
                "max_prompt_chars": 1000,
            },
        }
    }


@pytest.mark.asyncio
async def test_retrieve_chunks_service_embeds_retrieves_reranks_then_fetches_document_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.append(("embed", texts))
        return [[0.1]]

    async def fake_retrieve_chunks_client(embedding: list[float]) -> list[dict]:
        calls.append(("retrieve", embedding))
        return [{"document": "doc"}]

    async def fake_rerank_chunks_client(
        question: str, chunks: list[dict]
    ) -> list[dict]:
        calls.append(("rerank", question, chunks))
        return [
            {"document": "reranked-a", "metadata": {"path": "a.md"}},
            {"document": "reranked-a-duplicate", "metadata": {"path": "a.md"}},
            {"document": "reranked-b", "metadata": {"path": "b.md"}},
        ]

    async def fake_retrieve_document_chunks_client(paths: list[str]) -> list[dict]:
        calls.append(("documents", paths))
        return [{"document": "document chunks"}]

    monkeypatch.setattr(retrieve_chunks_service, "embed", fake_embed)
    monkeypatch.setattr(
        retrieve_chunks_service, "retrieve_chunks_client", fake_retrieve_chunks_client
    )
    monkeypatch.setattr(
        retrieve_chunks_service, "rerank_chunks_client", fake_rerank_chunks_client
    )
    monkeypatch.setattr(
        retrieve_chunks_service,
        "retrieve_document_chunks_client",
        fake_retrieve_document_chunks_client,
    )

    response = await retrieve_chunks_service.retrieve_chunks("Question", _config())

    assert response.retrieved_chunks == [{"document": "document chunks"}]
    assert calls == [
        ("embed", ["Question"]),
        ("retrieve", [0.1]),
        ("rerank", "Question", [{"document": "doc"}]),
        ("documents", ["a.md", "b.md"]),
    ]


@pytest.mark.asyncio
async def test_retrieve_chunks_service_can_skip_fetching_all_chunks_by_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    config = _config()
    config["retrieval"]["fetch_all_chunks_by_path"] = False

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1]]

    async def fake_retrieve_chunks_client(embedding: list[float]) -> list[dict]:
        return [{"document": "doc"}]

    async def fake_rerank_chunks_client(
        question: str, chunks: list[dict]
    ) -> list[dict]:
        return [{"document": "reranked", "metadata": {"path": "a.md"}}]

    async def fake_retrieve_document_chunks_client(paths: list[str]) -> list[dict]:
        calls.append(("documents", paths))
        return [{"document": "document chunks"}]

    monkeypatch.setattr(retrieve_chunks_service, "embed", fake_embed)
    monkeypatch.setattr(
        retrieve_chunks_service, "retrieve_chunks_client", fake_retrieve_chunks_client
    )
    monkeypatch.setattr(
        retrieve_chunks_service, "rerank_chunks_client", fake_rerank_chunks_client
    )
    monkeypatch.setattr(
        retrieve_chunks_service,
        "retrieve_document_chunks_client",
        fake_retrieve_document_chunks_client,
    )

    response = await retrieve_chunks_service.retrieve_chunks("Question", config)

    assert response.retrieved_chunks == [
        {"document": "reranked", "metadata": {"path": "a.md"}}
    ]
    assert calls == []


def test_extract_unique_paths_keeps_first_occurrence_order() -> None:
    chunks = [
        {"metadata": {"path": "a.md"}},
        {"metadata": {"path": "a.md"}},
        {"metadata": {"path": "b.md"}},
        {"metadata": {}},
    ]

    assert retrieve_chunks_service.extract_unique_paths(chunks) == ["a.md", "b.md"]


@pytest.mark.asyncio
async def test_ask_question_to_local_model_builds_payload_and_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_retrieve_and_rerank_chunks(
        question: str, config: dict
    ) -> list[dict]:
        assert question == "Question"
        assert config == _config()
        return [{"document": "doc", "metadata": {"title": "Doc"}}]

    async def fake_llm_client(payload: dict, timeout_seconds: int, url: str) -> dict:
        assert payload["model"] == "local-model"
        assert payload["options"]["num_predict"] == 128
        assert timeout_seconds == 30
        assert url == "http://ollama/v1/chat/completions"
        return {"choices": [{"message": {"content": "answer"}}]}

    monkeypatch.setattr(
        ask_question_service,
        "retrieve_and_rerank_chunks",
        fake_retrieve_and_rerank_chunks,
    )
    monkeypatch.setattr(
        ask_question_service, "ask_question_to_llm_client", fake_llm_client
    )

    response = await ask_question_service.ask_question_to_local_model(
        "Question", _config()
    )

    assert response.llm_response == "answer"
    assert response.retrieved_documents == {"Doc": 1}
    assert response.model == "local-model"


@pytest.mark.asyncio
async def test_ask_question_to_api_builds_payload_tokens_and_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_retrieve_and_rerank_chunks(
        question: str, config: dict
    ) -> list[dict]:
        assert question == "Question"
        assert config == _config()
        return [{"document": "doc", "metadata": {"title": "Doc"}}]

    async def fake_api_client(
        payload: dict, endpoint: str, api_key: str | None
    ) -> dict:
        assert payload["model"] == "api-model"
        assert endpoint == "http://api/v1/responses"
        return {
            "output": [{}, {"content": [{"text": "api answer"}]}],
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        }

    async def fake_calculate_cost(**kwargs) -> float:
        return 0.123456

    monkeypatch.setattr(
        ask_question_service,
        "retrieve_and_rerank_chunks",
        fake_retrieve_and_rerank_chunks,
    )
    monkeypatch.setattr(
        ask_question_service, "ask_question_to_api_client", fake_api_client
    )
    monkeypatch.setattr(ask_question_service, "calculate_cost", fake_calculate_cost)

    response = await ask_question_service.ask_question_to_api(
        "Question", _config(), db_pool=object()
    )

    assert response.llm_response == "api answer"
    assert response.input_tokens == 10
    assert response.output_tokens == 5
    assert response.cost == 0.123456


class FakeOidcClient:
    def __init__(self, claims: dict, userinfo: dict | None = None):
        self.claims = claims
        self.userinfo = userinfo or {}
        self.userinfo_called = False

    def validate_token(self, token: str) -> dict:
        return self.claims

    async def get_userinfo(self, token: str) -> dict:
        self.userinfo_called = True
        return self.userinfo


@pytest.mark.asyncio
async def test_auth_service_merges_userinfo_for_oauth_user_token() -> None:
    oidc = FakeOidcClient(
        {"sub": "user-1", "type": "oauth-access-token"},
        {"email": "user@example.com", "groups": ["dev"]},
    )

    user = await AuthService(oidc).authenticate("token")

    assert oidc.userinfo_called
    assert user.email == "user@example.com"
    assert user.groups == ["dev"]


@pytest.mark.asyncio
async def test_auth_service_does_not_call_userinfo_for_machine_token() -> None:
    oidc = FakeOidcClient({"sub": "client-rag", "type": "oauth-access-token"})

    user = await AuthService(oidc).authenticate("token")

    assert not oidc.userinfo_called
    assert user.sub == "client-rag"


def test_user_identity_hashes_normalized_identifier_and_rejects_empty_values() -> None:
    assert build_user_id_from_email(
        " USER@Example.COM ", "secret"
    ) == build_user_id_from_identifier("user@example.com", "secret")

    with pytest.raises(ValueError):
        build_user_id_from_identifier("", "secret")

    with pytest.raises(ValueError):
        build_user_id_from_identifier("user", " ")
