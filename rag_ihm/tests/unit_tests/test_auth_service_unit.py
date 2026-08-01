from app.services.auth_service import (
    OidcConfig,
    _extract_user_groups,
    _normalize_groups,
    _oauth_state_binding,
    build_authorization_params,
)


def test_build_authorization_params_contains_required_oidc_values() -> None:
    config = OidcConfig(
        authorize_url="http://idp/auth",
        token_url="http://idp/token",
        client_id="client",
        client_secret="secret",
        redirect_uri="http://app/callback",
        scope="openid profile",
    )

    assert build_authorization_params(config, "state") == {
        "response_type": "code",
        "client_id": "client",
        "redirect_uri": "http://app/callback",
        "scope": "openid profile",
        "state": "state",
    }
    assert "secret" not in repr(config)


def test_extract_user_groups_supports_groups_roles_and_role() -> None:
    assert _extract_user_groups({"groups": ["admin"]}) == ["admin"]


def test_normalize_groups_accepts_strings_and_dicts() -> None:
    assert _normalize_groups([" Admin ", {"display_name": "RAG Admin"}]) == {
        "admin",
        "rag admin",
    }


def test_oauth_state_binding_changes_with_client_or_redirect_uri() -> None:
    first = _oauth_state_binding(
        OidcConfig("auth", "token", "client", "secret", "redirect", "openid")
    )
    second = _oauth_state_binding(
        OidcConfig("auth", "token", "other", "secret", "redirect", "openid")
    )

    assert first != second
