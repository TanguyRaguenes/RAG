import pytest

from app.core.exceptions import RetrieverContainerException, RerankerContainerException
from app.dal.clients import embedder_client, reranker_client, retriever_client


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeAsyncClient:
    calls: list[dict] = []

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": self.timeout})
        if "embed" in url:
            return FakeResponse({"embeded_text": [0.1, 0.2]})
        if "rerank" in url:
            return FakeResponse({"reranked_chunks": [{"document": "reranked"}]})
        if "document_chunks" in url:
            return FakeResponse({"chunks": [{"document": "document chunks"}]})
        return FakeResponse({"chunks": [{"document": "doc"}]})


@pytest.mark.asyncio
async def test_embed_question_posts_text_and_returns_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setenv("RAG_EMBEDDER_EMBED_QUESTION_URL", "http://embedder/embed_text")
    monkeypatch.setattr(embedder_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await embedder_client.embed_question("Question")

    assert result == [0.1, 0.2]
    assert FakeAsyncClient.calls == [
        {"url": "http://embedder/embed_text", "json": {"text": "Question"}, "timeout": 120}
    ]


@pytest.mark.asyncio
async def test_retrieve_chunks_posts_embedding_and_returns_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setenv("RAG_RETRIEVER_RETRIEVE_CHUNKS_URL", "http://retriever/retrieve_chunks")
    monkeypatch.setattr(retriever_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await retriever_client.retrieve_chunks([0.1])

    assert result == [{"document": "doc"}]
    assert FakeAsyncClient.calls == [
        {"url": "http://retriever/retrieve_chunks", "json": {"embeded_question": [0.1]}, "timeout": 180}
    ]


@pytest.mark.asyncio
async def test_retrieve_chunks_raises_domain_exception_when_url_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_RETRIEVER_RETRIEVE_CHUNKS_URL", raising=False)

    with pytest.raises(RetrieverContainerException) as exc_info:
        await retriever_client.retrieve_chunks([0.1])

    assert exc_info.value.details == {"env_var": "RAG_RETRIEVER_RETRIEVE_CHUNKS_URL"}


@pytest.mark.asyncio
async def test_retrieve_document_chunks_posts_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setenv(
        "RAG_RETRIEVER_RETRIEVE_DOCUMENT_CHUNKS_URL",
        "http://retriever/retrieve_document_chunks",
    )
    monkeypatch.setattr(retriever_client.httpx, "AsyncClient", FakeAsyncClient)

    paths = ["doc.md"]
    result = await retriever_client.retrieve_document_chunks(paths)

    assert result == [{"document": "document chunks"}]
    assert FakeAsyncClient.calls == [
        {
            "url": "http://retriever/retrieve_document_chunks",
            "json": {"paths": paths},
            "timeout": 180,
        }
    ]


@pytest.mark.asyncio
async def test_retrieve_document_chunks_raises_domain_exception_when_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_RETRIEVER_RETRIEVE_DOCUMENT_CHUNKS_URL", raising=False)

    with pytest.raises(RetrieverContainerException) as exc_info:
        await retriever_client.retrieve_document_chunks([])

    assert exc_info.value.details == {
        "env_var": "RAG_RETRIEVER_RETRIEVE_DOCUMENT_CHUNKS_URL"
    }


@pytest.mark.asyncio
async def test_rerank_chunks_posts_question_and_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setenv("RAG_RERANKER_RERANK_CHUNKS_URL", "http://reranker/rerank_chunks")
    monkeypatch.setattr(reranker_client.httpx, "AsyncClient", FakeAsyncClient)

    chunks = [{"id": "1", "document": "doc", "metadata": {}, "similarity": 0.8}]
    result = await reranker_client.rerank_chunks("Question", chunks)

    assert result == [{"document": "reranked"}]
    assert FakeAsyncClient.calls == [
        {
            "url": "http://reranker/rerank_chunks",
            "json": {"question": "Question", "chunks": chunks},
            "timeout": 180,
        }
    ]


@pytest.mark.asyncio
async def test_rerank_chunks_raises_domain_exception_when_url_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_RERANKER_RERANK_CHUNKS_URL", raising=False)

    with pytest.raises(RerankerContainerException) as exc_info:
        await reranker_client.rerank_chunks("Question", [])

    assert exc_info.value.details == {"env_var": "RAG_RERANKER_RERANK_CHUNKS_URL"}
