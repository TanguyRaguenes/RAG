from app.core.token_verifier import (
    _extract_client_id,
    _extract_expires_at,
    _extract_scopes,
)


def test_extract_client_id_prefers_explicit_client_id() -> None:
    assert _extract_client_id({"client_id": "client", "aud": "audience"}) == "client"


def test_extract_client_id_falls_back_to_audience() -> None:
    assert _extract_client_id({"aud": ["kilo-mcp-client"]}) == "kilo-mcp-client"


def test_extract_scopes_accepts_space_separated_scope() -> None:
    assert _extract_scopes({"scope": "openid email profile"}) == [
        "openid",
        "email",
        "profile",
    ]


def test_extract_expires_at_returns_integer() -> None:
    assert _extract_expires_at({"exp": "123"}) == 123
