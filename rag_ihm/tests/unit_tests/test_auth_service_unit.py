import base64
import json

from app.services.auth_service import (
    OidcConfig,
    _decode_jwt_payload_without_verification,
    _extract_user_groups,
    _merge_user_claims,
    _normalize_groups,
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


def test_extract_user_groups_supports_groups_roles_and_role() -> None:
    assert _extract_user_groups({"groups": ["admin"]}) == ["admin"]
    assert _extract_user_groups({"roles": "reader"}) == ["reader"]
    assert _extract_user_groups({"role": {"name": "rag_admin"}}) == [
        {"name": "rag_admin"}
    ]


def test_normalize_groups_accepts_strings_and_dicts() -> None:
    assert _normalize_groups([" Admin ", {"display_name": "RAG Admin"}]) == {
        "admin",
        "rag admin",
    }


def test_merge_user_claims_preserves_access_groups_when_id_claims_do_not_define_them() -> (
    None
):
    merged = _merge_user_claims(
        id_claims={"email": "user@example.com"},
        access_claims={"groups": ["rag_admin"], "sub": "123"},
    )

    assert merged["email"] == "user@example.com"
    assert merged["groups"] == ["rag_admin"]


def test_decode_jwt_payload_without_verification_reads_payload() -> None:
    payload = {"sub": "123", "email": "user@example.com"}
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    token = f"header.{encoded_payload.rstrip('=')}.signature"

    assert _decode_jwt_payload_without_verification(token) == payload


def test_decode_jwt_payload_without_verification_returns_empty_dict_on_invalid_token() -> (
    None
):
    assert _decode_jwt_payload_without_verification("invalid") == {}
