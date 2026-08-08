from datetime import date

import pytest

from app.core.exceptions import InvalidRequestError
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.services import usage_tracking_service as service


class FakeUsageRepository:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.calls = db_pool.setdefault("calls", [])

    async def upsert_user(self, **kwargs):
        self.calls.append(("upsert_user", kwargs))

    async def ensure_default_quota_rule(self, user_id: str, max_tokens_per_month: int):
        self.calls.append(("ensure_quota", user_id, max_tokens_per_month))

    async def create_session(self, user_id: str, channel: str) -> int:
        self.calls.append(("create_session", user_id, channel))
        return 42

    async def finish_session(self, session_id: int) -> None:
        self.calls.append(("finish_session", session_id))

    async def get_active_quota_usage(self, user_id: str):
        return self.db_pool.get("quota", (100, 10, True, False))

    async def get_quota_usage_details(self, user_id: str):
        return {
            "utilisateur_id": user_id,
            "email": "user@example.com",
            "display_name": "User Example",
            "preferred_username": "user",
            "max_tokens_par_mois": 100,
            "consumed_tokens": 25,
            "actif": True,
            "illimite": False,
            "date_debut": date(2026, 1, 1),
            "date_fin": date(2026, 1, 31),
        }

    async def update_quota_rule(self, **kwargs):
        self.calls.append(("update_quota", kwargs))

    async def upsert_feedback(self, **kwargs):
        self.calls.append(("feedback", kwargs))

    async def list_interaction_feedbacks(self, **kwargs):
        return [
            {
                "interaction_id": 1,
                "cree_le": date(2026, 1, 1),
                "question": "Q",
                "reponse": "A",
                "note": 1,
                "commentaire": "ok",
                "chunks": '[{"rang": 1, "score": 0.9, "titre": "Doc", "chemin": "doc.md", "contenu": "doc"}]',
            }
        ]

    async def save_successful_interaction(self, **kwargs) -> int:
        self.calls.append(("successful", kwargs))
        return 123

    async def save_failed_interaction(self, **kwargs) -> int:
        self.calls.append(("failed", kwargs))
        return 124


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(
        issuer="issuer",
        sub="user-sub",
        email="USER@Example.COM",
        display_name="User Example",
        preferred_username="user",
        groups=["Admin"],
    )


def _user_without_email() -> AuthenticatedUser:
    return AuthenticatedUser(issuer="issuer", sub="user-sub")


@pytest.fixture(autouse=True)
def fake_repository(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("USER_HASH_SECRET", "secret")
    monkeypatch.setattr(service, "UsageRepository", FakeUsageRepository)


@pytest.mark.asyncio
async def test_start_and_finish_usage_session_use_repository() -> None:
    db_pool = {}

    user_id, session_id = await service.start_usage_session(
        _user(), db_pool, "streamlit"
    )
    await service.finish_usage_session(db_pool, session_id)

    assert session_id == 42
    assert db_pool["calls"][1] == ("ensure_quota", user_id, 100000)
    assert db_pool["calls"][-1] == ("finish_session", 42)


@pytest.mark.asyncio
async def test_usage_user_id_is_stable_when_email_is_missing() -> None:
    db_pool = {}

    user_id_with_email = await service.ensure_usage_user_exists(_user(), db_pool)
    user_id_without_email = await service.ensure_usage_user_exists(
        _user_without_email(), db_pool
    )

    assert user_id_with_email == user_id_without_email


@pytest.mark.asyncio
async def test_check_user_token_quota_raises_when_inactive_or_exceeded() -> None:
    await service.check_user_token_quota({"quota": (100, 10, True, False)}, "user")

    with pytest.raises(service.QuotaInactiveError):
        await service.check_user_token_quota(
            {"quota": (100, 10, False, False)}, "user"
        )

    with pytest.raises(service.QuotaExceededError):
        await service.check_user_token_quota(
            {"quota": (100, 100, True, False)}, "user"
        )


@pytest.mark.asyncio
async def test_check_user_token_quota_allows_unlimited_active_user() -> None:
    await service.check_user_token_quota(
        {"quota": (100, 1000, True, True)}, "user"
    )

    with pytest.raises(service.QuotaInactiveError):
        await service.check_user_token_quota(
            {"quota": (100, 1000, False, True)}, "user"
        )


@pytest.mark.asyncio
async def test_feedback_and_admin_feedbacks_are_mapped() -> None:
    db_pool = {}

    feedback = await service.save_current_user_feedback(
        _user(), db_pool, 1, 1, "  ok  "
    )
    rows = await service.list_admin_interaction_feedbacks(
        db_pool, date(2026, 1, 1), date(2026, 1, 31)
    )

    assert feedback.commentaire == "ok"
    assert rows[0].chunks[0].contenu == "doc"

    with pytest.raises(InvalidRequestError):
        await service.list_admin_interaction_feedbacks(
            db_pool, date(2026, 2, 1), date(2026, 1, 1)
        )
