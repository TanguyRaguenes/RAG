from typing import ClassVar

import httpx
import pytest
from app.core.exceptions import (
    DependencyResponseError,
    IdentityProviderError,
    LlmApiException,
)
from app.dal.clients import llm_client, oidc_client


class FakeResponse:
    def __init__(self, payload, status_code: int = 200, text: str = ""):
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.request = httpx.Request("POST", "http://llm")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self):
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class FakeAsyncClient:
    calls: ClassVar[list[dict]] = []
    response = FakeResponse({"ok": True})

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict, headers=None) -> FakeResponse:
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": self.timeout,
            }
        )
        return self.response

    async def get(self, url: str, headers=None) -> FakeResponse:
        self.calls.append(
            {"method": "GET", "url": url, "headers": headers, "timeout": self.timeout}
        )
        return self.response


@pytest.mark.asyncio
async def test_ask_question_to_llm_posts_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"choices": []})
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await llm_client.ask_question_to_llm({"model": "m"}, 12, "http://llm")

    assert result == {"choices": []}
    assert FakeAsyncClient.calls == [
        {
            "method": "POST",
            "url": "http://llm",
            "json": {"model": "m"},
            "headers": None,
            "timeout": 12,
        }
    ]


@pytest.mark.asyncio
async def test_ask_question_to_api_sends_bearer_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"output": []})
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await llm_client.ask_question_to_api({"model": "m"}, "http://api", "key")

    assert result == {"output": []}
    assert FakeAsyncClient.calls[0]["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer key",
    }


@pytest.mark.asyncio
async def test_ask_question_to_llm_wraps_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse({}, status_code=500, text="down")
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(
        LlmApiException, match="Local LLM returned an HTTP error"
    ) as error:
        await llm_client.ask_question_to_llm({}, 12, "http://llm")

    assert error.value.details == {"status_code": 500, "error_type": "http_status"}
    assert error.value.original_exception is None
    assert isinstance(error.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.asyncio
async def test_ask_question_to_api_does_not_store_upstream_http_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse(
        {"error": "sensitive"}, status_code=429, text="sensitive body"
    )
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(
        LlmApiException, match="LLM API returned an HTTP error"
    ) as error:
        await llm_client.ask_question_to_api({}, "http://private-api", "key")

    assert error.value.details == {"status_code": 429, "error_type": "http_status"}
    assert error.value.original_exception is None
    assert isinstance(error.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_message"),
    [
        ("local", "Local LLM returned invalid JSON"),
        ("api", "LLM API returned invalid JSON"),
    ],
)
async def test_llm_clients_wrap_successful_non_json_response_and_record_metric(
    operation: str,
    expected_message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors = []
    FakeAsyncClient.response = FakeResponse(ValueError("private upstream body"))
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        llm_client,
        "_record_external_error",
        lambda dependency, metric_operation, error_type, start: errors.append(
            (dependency, metric_operation, error_type)
        ),
    )

    with pytest.raises(DependencyResponseError, match=expected_message) as error:
        if operation == "local":
            await llm_client.ask_question_to_llm({}, 12, "http://llm")
        else:
            await llm_client.ask_question_to_api({}, "http://api", "key")

    assert error.value.details == {
        "dependency": "llm",
        "operation": f"{operation}_llm",
    }
    assert errors == [("llm", f"{operation}_llm", "invalid_json")]
    assert error.value.original_exception is None
    assert isinstance(error.value.__cause__, ValueError)


def test_public_llm_error_does_not_expose_upstream_details() -> None:
    exception = LlmApiException(
        internal_message="LLM API returned an HTTP error",
        details={"url": "http://llm/private", "error": "raw upstream response"},
        original_exception={
            "slug": "UPSTREAM",
            "message": "sensitive",
            "details": {"response": "secret"},
        },
    )

    assert exception.to_public_dict() == {
        "slug": "ERR_LLM_API",
        "message": "Le service de génération est temporairement indisponible.",
        "details": {},
    }


@pytest.mark.asyncio
async def test_oidc_get_userinfo_returns_empty_dict_without_url() -> None:
    client = oidc_client.OidcClient("issuer", "http://jwks", userinfo_url=None)

    assert await client.get_userinfo("token") == {}


@pytest.mark.asyncio
async def test_oidc_get_userinfo_calls_userinfo_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"email": "user@example.com"})
    monkeypatch.setattr(oidc_client.httpx, "AsyncClient", FakeAsyncClient)
    client = oidc_client.OidcClient(
        "issuer", "http://jwks", userinfo_url="http://userinfo"
    )

    assert await client.get_userinfo("token") == {"email": "user@example.com"}
    assert FakeAsyncClient.calls == [
        {
            "method": "GET",
            "url": "http://userinfo",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 10,
        }
    ]


@pytest.mark.asyncio
async def test_oidc_client_translates_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse(ValueError("private response"))
    monkeypatch.setattr(oidc_client.httpx, "AsyncClient", FakeAsyncClient)
    client = oidc_client.OidcClient(
        "issuer", "http://jwks", userinfo_url="http://userinfo"
    )

    with pytest.raises(IdentityProviderError):
        await client.get_userinfo("token")
