from datetime import date

import pytest

from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.services import usage_tracking_service as service


class FakeUsageRepository:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.calls = db_pool.setdefault("calls", [])

    async def upsert_user(self, user_id: str, email: str | None):
        self.calls.append(("upsert_user", user_id, email))

    async def ensure_default_quota_rule(self, user_id: str, max_tokens_per_month: int):
        self.calls.append(("ensure_quota", user_id, max_tokens_per_month))

    async def create_session(self, user_id: str, channel: str) -> int:
        self.calls.append(("create_session", user_id, channel))
        return 42

    async def finish_session(self, session_id: int) -> None:
        self.calls.append(("finish_session", session_id))

    async def get_active_quota_usage(self, user_id: str):
        return self.db_pool.get("quota", (100, 10, True))

    async def get_quota_usage_details(self, user_id: str):
        return {
            "utilisateur_id": user_id,
            "email": "user@example.com",
            "max_tokens_par_mois": 100,
            "consumed_tokens": 25,
            "actif": True,
            "date_debut": date(2026, 1, 1),
            "date_fin": date(2026, 1, 31),
        }

    async def update_quota_rule(self, **kwargs):
        self.calls.append(("update_quota", kwargs))

    async def get_user_theme_preference(self, user_id: str) -> str:
        return "Sombre"

    async def update_user_theme_preference(self, **kwargs):
        self.calls.append(("theme", kwargs))

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
    return AuthenticatedUser(sub="user-sub", email="USER@Example.COM", groups=["Admin"])


@pytest.fixture(autouse=True)
def fake_repository(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("USER_HASH_SECRET", "secret")
    monkeypatch.setattr(service, "UsageRepository", FakeUsageRepository)


@pytest.mark.asyncio
async def test_start_and_finish_usage_session_use_repository() -> None:
    db_pool = {}

    user_id, session_id = await service.start_usage_session(_user(), db_pool, "streamlit")
    await service.finish_usage_session(db_pool, session_id)

    assert session_id == 42
    assert db_pool["calls"][1] == ("ensure_quota", user_id, 100000)
    assert db_pool["calls"][-1] == ("finish_session", 42)


@pytest.mark.asyncio
async def test_check_user_token_quota_raises_when_inactive_or_exceeded() -> None:
    await service.check_user_token_quota({"quota": (100, 10, True)}, "user")

    with pytest.raises(service.QuotaInactiveError):
        await service.check_user_token_quota({"quota": (100, 10, False)}, "user")

    with pytest.raises(service.QuotaExceededError):
        await service.check_user_token_quota({"quota": (100, 100, True)}, "user")


@pytest.mark.asyncio
async def test_preferences_feedback_and_admin_feedbacks_are_mapped() -> None:
    db_pool = {}

    preferences = await service.update_current_user_preferences(_user(), db_pool, "Clair")
    feedback = await service.save_current_user_feedback(_user(), db_pool, 1, 1, "  ok  ")
    rows = await service.list_admin_interaction_feedbacks(db_pool, date(2026, 1, 1), date(2026, 1, 31))

    assert preferences.theme_preference == "Clair"
    assert feedback.commentaire == "ok"
    assert rows[0].chunks[0].contenu == "doc"

    with pytest.raises(ValueError):
        await service.update_current_user_preferences(_user(), db_pool, "Invalid")

    with pytest.raises(ValueError):
        await service.list_admin_interaction_feedbacks(db_pool, date(2026, 2, 1), date(2026, 1, 1))
