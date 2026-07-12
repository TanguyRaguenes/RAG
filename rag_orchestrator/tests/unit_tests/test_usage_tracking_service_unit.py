from datetime import datetime, timezone

import pytest

from app.services.usage_tracking_service import (
    _decode_chunks,
    _get_default_user_monthly_token_quota,
    _normalize_groups,
    _normalize_optional_comment,
    _normalize_optional_email,
    _quota_row_to_response,
)


def test_get_default_user_monthly_token_quota_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEFAULT_USER_MONTHLY_TOKEN_QUOTA", raising=False)

    assert _get_default_user_monthly_token_quota() == 100000


def test_get_default_user_monthly_token_quota_rejects_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEFAULT_USER_MONTHLY_TOKEN_QUOTA", "0")

    with pytest.raises(ValueError):
        _get_default_user_monthly_token_quota()

    monkeypatch.setenv("DEFAULT_USER_MONTHLY_TOKEN_QUOTA", "abc")

    with pytest.raises(ValueError):
        _get_default_user_monthly_token_quota()


def test_quota_row_to_response_calculates_remaining_tokens_and_ratio() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = {
        "utilisateur_id": "user-1",
        "email": "user@example.com",
        "max_tokens_par_mois": 100,
        "consumed_tokens": 125,
        "actif": True,
        "date_debut": start,
        "date_fin": None,
    }

    response = _quota_row_to_response(row)

    assert response.remaining_tokens == 0
    assert response.usage_ratio == 1.0
    assert response.date_debut == start


def test_normalize_groups_trims_and_lowercases_values() -> None:
    assert _normalize_groups([" Admin ", "", "RAG_Admin"]) == {"admin", "rag_admin"}


def test_normalize_optional_values_return_none_for_empty_values() -> None:
    assert _normalize_optional_email(" USER@EXAMPLE.COM ") == "user@example.com"
    assert _normalize_optional_email("   ") is None
    assert _normalize_optional_comment(" commentaire ") == "commentaire"
    assert _normalize_optional_comment("   ") is None


def test_decode_chunks_accepts_list_or_json_list() -> None:
    chunks = [{"document": "chunk"}]

    assert _decode_chunks(chunks) == chunks
    assert _decode_chunks('[{"document": "chunk"}]') == chunks


def test_decode_chunks_rejects_invalid_or_non_list_values() -> None:
    assert _decode_chunks('{"document": "chunk"}') == []
    assert _decode_chunks("not json") == []
    assert _decode_chunks(None) == []
