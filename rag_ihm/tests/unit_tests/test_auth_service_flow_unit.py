from urllib.parse import parse_qs, urlparse

import pytest
from app.components import common
from app.core.errors import RagApiError
from app.services import auth_service
from app.services.auth_service import OidcConfig


class StopCalled(Exception):
    pass


class QueryParams(dict[str, str]):
    def __init__(self) -> None:
        super().__init__()
        self.cleared = False

    def clear(self) -> None:
        self.cleared = True
        super().clear()


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.query_params = QueryParams()
        self.errors: list[str] = []
        self.titles: list[str] = []
        self.captions: list[str] = []
        self.html_blocks: list[str] = []
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


def test_get_required_env_raises_safe_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISSING_ENV", raising=False)

    with pytest.raises(RagApiError) as raised:
        auth_service._get_required_env("MISSING_ENV")

    assert raised.value.code == "configuration_error"
    assert raised.value.safe_details == {"configuration": "MISSING_ENV"}


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
    assert auth_service._is_valid_oauth_state(
        state,
        "secret",
        auth_service._oauth_state_binding(_oidc_config()),
    )
    assert fake_st.session_state == {}


def test_exchange_code_for_tokens_posts_oidc_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []

    class FakeOidcClient:
        def __init__(self, http_client: object) -> None:
            pass

        def exchange_code(self, **kwargs: str) -> dict[str, str]:
            calls.append(kwargs)
            return {"access_token": "token"}

    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)
    monkeypatch.setattr(auth_service, "OidcClient", FakeOidcClient)

    assert auth_service._exchange_code_for_tokens("code") == {"access_token": "token"}
    assert calls[0]["code"] == "code"
    assert calls[0]["token_url"] == "http://token"


def test_handle_oidc_callback_stores_tokens_and_user_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)
    monkeypatch.setattr(auth_service.time, "time", lambda: 1000)
    state = auth_service._build_oauth_state(
        "secret", auth_service._oauth_state_binding(_oidc_config())
    )
    fake_st.query_params.update({"code": "code", "state": state})
    monkeypatch.setattr(
        auth_service,
        "_exchange_code_for_tokens",
        lambda code: {
            "access_token": "access-token",
            "refresh_token": "refresh",
        },
    )
    monkeypatch.setattr(auth_service, "load_chat_api_config", lambda: object())
    monkeypatch.setattr(
        auth_service,
        "get_authenticated_user",
        lambda config, token: {
            "issuer": "http://issuer",
            "sub": "user",
            "email": "user@example.com",
            "groups": ["dev"],
        },
    )

    auth_service.handle_oidc_callback()

    assert fake_st.session_state[auth_service.ACCESS_TOKEN_KEY]
    assert fake_st.session_state[auth_service.USER_KEY]["email"] == "user@example.com"
    assert fake_st.session_state[auth_service.USER_KEY]["groups"] == ["dev"]
    assert fake_st.session_state[auth_service.IDENTITY_VERIFIED_KEY] is True
    assert fake_st.query_params.cleared
    assert fake_st.rerun_called


def test_handle_oidc_callback_stops_on_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params.update({"code": "code", "state": "bad"})
    fake_st.session_state[auth_service.ACCESS_TOKEN_KEY] = "token"
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(common, "st", fake_st)
    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)

    with pytest.raises(StopCalled):
        auth_service.handle_oidc_callback()

    assert auth_service.ACCESS_TOKEN_KEY not in fake_st.session_state
    assert fake_st.query_params == {}


def test_callback_failure_removes_oauth_params_before_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params.update(
        {"code": "code", "state": "state", "error": "denied", "page": "chat"}
    )
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(common, "st", fake_st)

    with pytest.raises(StopCalled):
        auth_service.handle_oidc_callback()

    assert fake_st.query_params == {"page": "chat"}
    assert fake_st.errors == ["Authentification refusée par Pocket ID."]


def test_handle_oidc_callback_rejects_identity_not_verified_by_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(auth_service, "st", fake_st)
    monkeypatch.setattr(common, "st", fake_st)
    monkeypatch.setattr(auth_service, "get_oidc_config", _oidc_config)
    monkeypatch.setattr(auth_service.time, "time", lambda: 1000)
    state = auth_service._build_oauth_state(
        "secret", auth_service._oauth_state_binding(_oidc_config())
    )
    fake_st.query_params.update({"code": "code", "state": state})
    fake_st.session_state["chat_messages"] = [{"content": "private"}]
    monkeypatch.setattr(
        auth_service,
        "_exchange_code_for_tokens",
        lambda code: {"access_token": "invalid-token"},
    )
    monkeypatch.setattr(auth_service, "load_chat_api_config", lambda: object())

    def reject_user(config: object, token: str) -> None:
        raise auth_service.RagApiError("invalid")

    monkeypatch.setattr(auth_service, "get_authenticated_user", reject_user)

    with pytest.raises(StopCalled):
        auth_service.handle_oidc_callback()

    assert fake_st.session_state == {}
    assert fake_st.errors == [
        "L'identité Pocket ID n'a pas pu être vérifiée par le service RAG."
    ]


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


def test_logout_removes_all_user_session_data(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_st = FakeStreamlit()
    fake_st.session_state.update(
        {
            auth_service.ACCESS_TOKEN_KEY: "token",
            auth_service.USER_KEY: {"sub": "user"},
            "chat_messages": [{"content": "private"}],
            "dashboard_result": {"score": 1},
            "feedback_comment_1": "private",
        }
    )
    fake_st.query_params["code"] = "oauth-code"
    monkeypatch.setattr(auth_service, "st", fake_st)

    auth_service.logout()

    assert fake_st.session_state == {}
    assert fake_st.query_params == {}


def test_auth_session_accessors_and_admin_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = FakeStreamlit()
    fake_st.session_state[auth_service.ACCESS_TOKEN_KEY] = "token"
    fake_st.session_state[auth_service.USER_KEY] = {
        "issuer": "issuer",
        "sub": "user",
        "groups": ["rag_admin"],
    }
    assert not auth_service.is_authenticated()
    fake_st.session_state[auth_service.IDENTITY_VERIFIED_KEY] = True
    monkeypatch.setattr(auth_service, "st", fake_st)

    assert auth_service.is_authenticated()
    assert auth_service.get_access_token() == "token"
    assert auth_service.get_current_user() == {
        "issuer": "issuer",
        "sub": "user",
        "groups": ["rag_admin"],
    }
    user = {"issuer": "issuer", "sub": "user", "groups": ["rag_admin"]}
    assert auth_service.is_usage_admin(user)
    assert auth_service.is_evaluator_admin(user)
    assert not auth_service.is_usage_admin(None)


def test_usage_and_evaluator_admin_groups_are_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_USAGE_ADMIN_GROUPS", "usage_admin")
    monkeypatch.setenv("RAG_EVALUATOR_ADMIN_GROUPS", "evaluator_admin")

    usage_user = {"issuer": "issuer", "sub": "usage", "groups": ["usage_admin"]}
    evaluator_user = {
        "issuer": "issuer",
        "sub": "evaluator",
        "groups": ["evaluator_admin"],
    }

    assert auth_service.is_usage_admin(usage_user)
    assert not auth_service.is_evaluator_admin(usage_user)
    assert auth_service.is_evaluator_admin(evaluator_user)
    assert not auth_service.is_usage_admin(evaluator_user)
