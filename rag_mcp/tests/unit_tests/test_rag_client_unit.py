from types import TracebackType
from typing import ClassVar, Self

import httpx
import pytest
from app.core.config import McpConfig
from app.core.errors import (
    McpConnectionError,
    McpForbiddenError,
    McpInvalidJsonError,
    McpRateLimitError,
    McpResponseContractError,
    McpTimeoutError,
    McpUnauthorizedError,
    McpUpstreamHttpError,
    McpUpstreamServerError,
)
from app.dal.clients.rag_client import RagClient
from app.schemas.rag_response import RetrievedChunksResponse


def _config() -> McpConfig:
    return McpConfig(
        rag_orchestrator_url="http://rag/retrieve_chunks",
        oidc_issuer="https://auth.example.test",
        oidc_jwks_uri="https://auth.example.test/jwks.json",
        oidc_allowed_audiences=("https://mcp.example.test/",),
        required_scopes=("rag:mcp",),
        resource_server_url="https://mcp.example.test",
    )


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

    def json(self) -> object:
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class FakeAsyncClient:
    calls: ClassVar[list[dict]] = []

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        return False

    async def post(self, url: str, json: dict, headers: dict) -> FakeResponse:
        self.calls.append(
            {"url": url, "json": json, "headers": headers, "timeout": self.timeout}
        )
        return FakeResponse({"retrieved_chunks": [{"document": "doc"}]})


@pytest.mark.asyncio
async def test_retrieve_documentation_chunks_posts_question_with_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    result = await RagClient(
        _config(), client_factory=FakeAsyncClient
    ).retrieve_documentation_chunks(
        "Comment deployer ?",
        "token",
    )

    assert result.retrieved_chunks == ({"document": "doc"},)
    assert FakeAsyncClient.calls == [
        {
            "url": "http://rag/retrieve_chunks",
            "json": {"question": "Comment deployer ?"},
            "headers": {"Authorization": "Bearer token"},
            "timeout": 120,
        }
    ]


def test_retrieved_chunks_response_rejects_missing_contract_key() -> None:
    with pytest.raises(McpResponseContractError) as raised:
        RetrievedChunksResponse.from_payload({})

    assert raised.value.code == "upstream_contract_error"
    assert "retrieved_chunks" not in raised.value.public_message


class FailingAsyncClient(FakeAsyncClient):
    failure: ClassVar[BaseException]

    async def post(self, url: str, json: dict, headers: dict) -> FakeResponse:
        raise self.failure


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        (httpx.ReadTimeout("slow"), McpTimeoutError),
        (
            httpx.ConnectError(
                "secret endpoint",
                request=httpx.Request("POST", "https://secret.example"),
            ),
            McpConnectionError,
        ),
    ],
)
async def test_rag_client_classifies_transport_errors_without_sensitive_details(
    failure: BaseException,
    expected_error: type[Exception],
) -> None:
    FailingAsyncClient.failure = failure

    with pytest.raises(expected_error) as raised:
        await RagClient(
            _config(), client_factory=FailingAsyncClient
        ).retrieve_documentation_chunks("private question", "secret-token")

    assert raised.value.safe_details == {
        "dependency": "rag_orchestrator",
        "operation": "retrieve_documentation_chunks",
    }
    assert "secret" not in str(raised.value)


class StatusAsyncClient(FakeAsyncClient):
    status_code: ClassVar[int]

    async def post(self, url: str, json: dict, headers: dict) -> httpx.Response:
        request = httpx.Request("POST", "https://secret.example")
        return httpx.Response(
            self.status_code,
            text="private backend body",
            request=request,
        )


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (400, McpUpstreamHttpError),
        (401, McpUnauthorizedError),
        (403, McpForbiddenError),
        (429, McpRateLimitError),
        (503, McpUpstreamServerError),
    ],
)
async def test_rag_client_classifies_http_status_without_body_or_url(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    StatusAsyncClient.status_code = status_code

    with pytest.raises(expected_error) as raised:
        await RagClient(
            _config(), client_factory=StatusAsyncClient
        ).retrieve_documentation_chunks("private question", "secret-token")

    assert raised.value.safe_details == {
        "dependency": "rag_orchestrator",
        "status_code": status_code,
    }
    assert "private backend body" not in str(raised.value)
    assert "secret.example" not in repr(raised.value.safe_details)


class InvalidJsonAsyncClient(FakeAsyncClient):
    async def post(self, url: str, json: dict, headers: dict) -> FakeResponse:
        return FakeResponse(ValueError("private response body"))


async def test_rag_client_classifies_invalid_json_without_response_body() -> None:
    with pytest.raises(McpInvalidJsonError) as raised:
        await RagClient(
            _config(), client_factory=InvalidJsonAsyncClient
        ).retrieve_documentation_chunks("private question", "secret-token")

    assert raised.value.code == "upstream_invalid_json"
    assert "private response body" not in str(raised.value)
