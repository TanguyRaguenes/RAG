import base64
import json
from urllib.parse import parse_qs, urlparse

import pytest

from app.services import auth_service
from app.services.auth_service import OidcConfig


class StopCalled(Exception):
    pass


class QueryParams(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleared = False

    def clear(self):
        self.cleared = True
        super().clear()


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.query_params = QueryParams()
        self.errors = []
        self.titles = []
        self.captions = []
        self.html_blocks = []
        self.rerun_called = False

    def error(self, message: str) -> None:
        self.errors.append(message)

    def title(self, message: str) -> None:
        self.titles.append(message)

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def html(self, body: str) -> None:
        self.html_blocks.append(body)

    def stop(self) -> None:
        raise StopCalled()

    def rerun(self) -> None:
        self.rerun_called = True


def _jwt_payload(payload: dict) -> str:
    encoded = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    )
    return f"header.{encoded}.signature"


def _oidc_config() -> OidcConfig:
    return OidcConfig(
        "http://authorize",
        "http://token",
        "client",
        "secret",
        "http://redirect",
        "openid",
    )


def test_get_oidc_config_reads_required_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_IHM_OIDC_AUTHORIZE_URL", "http://authorize")
    monkeypatch.setenv("RAG_IHM_OIDC_TOKEN_URL", "http://token")
    monkeypatch.setenv("RAG_IHM_OIDC_CLIENT_ID", "client")
    monkeypatch.setenv("RAG_IHM_OIDC_CLIENT_SECRET", "secret")
    monkeypatch.setenv("RAG_IHM_OIDC_REDIRECT_URI", "http://redirect")

    config = auth_service.get_oidc_config()

    assert config.authorize_url == "http://authorize"
    assert config.scope == "openid email profile groups"


def test_get_required_env_stops_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.delenv("MISSING_ENV", raising=False)

    with pytest.raises(StopCalled):
        auth_service._get_required_env("MISSING_ENV")

    assert fake_st.errors == ["Variable d'environnement manquante : MISSING_ENV"]


def test_build_login_url_signs_state_and_encodes_authorization_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)
    monkeypatch.setattr(auth_service.secrets, "token_urlsafe", lambda size: "nonce")
    monkeypatch.setattr(auth_service.time, "time", lambda: 1000)

    url = auth_service.build_login_url()
    params = parse_qs(urlparse(url).query)
    state = params["state"][0]

    assert url.startswith("http://authorize?")
    assert params["client_id"] == ["client"]
    assert params["redirect_uri"] == ["http://redirect"]
    assert state.startswith("1000.nonce.")
    assert auth_service._is_valid_oauth_state(state, "secret")
    assert fake_st.session_state == {}


def test_exchange_code_for_tokens_posts_oidc_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "token"}

    def fake_post(url, data, headers, timeout):
        calls.append({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return Response()

    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)
    monkeypatch.setattr(auth_service.requests, "post", fake_post)

    assert auth_service._exchange_code_for_tokens("code") == {"access_token": "token"}
    assert calls[0]["data"]["grant_type"] == "authorization_code"
    assert calls[0]["data"]["code"] == "code"


def test_handle_oidc_callback_stores_tokens_and_user_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)
    monkeypatch.setattr(auth_service.time, "time", lambda: 1000)
    state = auth_service._build_oauth_state("secret")
    fake_st.query_params.update({"code": "code", "state": state})
    monkeypatch.setattr(
        auth_service,
        "_exchange_code_for_tokens",
        lambda code: {
            "access_token": _jwt_payload({"sub": "user", "groups": ["dev"]}),
            "id_token": _jwt_payload({"email": "user@example.com"}),
            "refresh_token": "refresh",
        },
    )

    auth_service.handle_oidc_callback()

    assert fake_st.session_state[auth_service.ACCESS_TOKEN_KEY]
    assert fake_st.session_state[auth_service.USER_KEY]["email"] == "user@example.com"
    assert fake_st.session_state[auth_service.USER_KEY]["groups"] == ["dev"]
    assert fake_st.query_params.cleared
    assert fake_st.rerun_called


def test_handle_oidc_callback_stops_on_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params.update({"code": "code", "state": "bad"})
    fake_st.session_state[auth_service.ACCESS_TOKEN_KEY] = "token"
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)

    with pytest.raises(StopCalled):
        auth_service.handle_oidc_callback()

    assert auth_service.ACCESS_TOKEN_KEY not in fake_st.session_state


def test_oauth_state_expires_after_ten_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_service.time, "time", lambda: 1000)
    state = auth_service._build_oauth_state("secret")
    monkeypatch.setattr(auth_service.time, "time", lambda: 1601)

    assert not auth_service._is_valid_oauth_state(state, "secret")


def test_require_authenticated_user_renders_same_tab_login_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(
        auth_service,
        "build_login_url",
        lambda: 'https://idp.example/login?state=abc&return="app"',
    )

    with pytest.raises(StopCalled):
        auth_service.require_authenticated_user()

    assert fake_st.titles == ["IsiDore"]
    assert fake_st.html_blocks == [
        '<a href="https://idp.example/login?state=abc&amp;return=&quot;app&quot;" target="_self">Se connecter</a>'
    ]


def test_logout_removes_auth_session_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_st = FakeStreamlit()
    for key in auth_service.AUTH_SESSION_KEYS:
        fake_st.session_state[key] = "value"
    monkeypatch.setattr(auth_service, "st", fake_st)

    auth_service.logout()

    assert fake_st.session_state == {}


def test_auth_session_accessors_and_admin_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    fake_st.session_state[auth_service.ACCESS_TOKEN_KEY] = "token"
    fake_st.session_state[auth_service.USER_KEY] = {"groups": ["rag_admin"]}
    monkeypatch.setattr(auth_service, "st", fake_st)

    assert auth_service.is_authenticated()
    assert auth_service.get_access_token() == "token"
    assert auth_service.get_current_user() == {"groups": ["rag_admin"]}
    assert auth_service.is_usage_admin({"groups": ["rag_admin"]})
    assert not auth_service.is_usage_admin(None)
