import asyncpg
import pytest

from app.core.exceptions import DatabaseError
from app.dal.repositories.interaction_repository import _get_chunk_score
from app.dal.repositories.usage_repository import UsageRepository, _to_decimal_or_none


def test_to_decimal_or_none_preserves_decimal_precision() -> None:
    assert _to_decimal_or_none(None) is None
    assert str(_to_decimal_or_none(0.123456)) == "0.123456"


def test_get_chunk_score_prefers_reranker_score() -> None:
    assert _get_chunk_score({"rerank_score": 0.9, "similarity": 0.4}) == 0.9
    assert _get_chunk_score({"similarity": 0.4}) == 0.4
    assert _get_chunk_score({"rerank_score": "invalid"}) is None


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeQuotaConnection:
    def __init__(self, close_result: str = "UPDATE 1") -> None:
        self.close_result = close_result
        self.calls = []

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    async def execute(self, query: str, *args):
        self.calls.append((query, args))
        if query.lstrip().startswith("UPDATE"):
            return self.close_result
        return "INSERT 0 1"


class FakeQuotaPool:
    def __init__(self, connection: FakeQuotaConnection) -> None:
        self.connection = connection

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.connection)


@pytest.mark.asyncio
async def test_update_quota_rule_closes_then_inserts_version() -> None:
    connection = FakeQuotaConnection()
    repository = UsageRepository(FakeQuotaPool(connection))

    await repository.update_quota_rule(
        user_id="user-1",
        max_tokens_per_month=200,
        active=True,
    )

    assert len(connection.calls) == 2
    assert "SET actif = false" in connection.calls[0][0]
    assert "date_fin = now()" in connection.calls[0][0]
    assert connection.calls[0][1] == ("user-1",)
    assert "INSERT INTO quota_utilisateur" in connection.calls[1][0]
    assert connection.calls[1][1] == ("user-1", 200, True)


@pytest.mark.asyncio
async def test_update_quota_rule_rejects_unknown_user() -> None:
    repository = UsageRepository(FakeQuotaPool(FakeQuotaConnection("UPDATE 0")))

    with pytest.raises(ValueError, match="Unknown user quota"):
        await repository.update_quota_rule(
            user_id="missing",
            max_tokens_per_month=200,
            active=True,
        )


class FailingDatabaseConnection:
    async def execute(self, query: str, *args: object) -> None:
        raise asyncpg.PostgresError("private database diagnostic")


@pytest.mark.asyncio
async def test_repository_translates_asyncpg_errors_at_boundary() -> None:
    repository = UsageRepository(FakeQuotaPool(FailingDatabaseConnection()))

    with pytest.raises(DatabaseError) as error:
        await repository.finish_session(1)

    assert error.value.to_dict() == {
        "slug": "ERR_DATABASE",
        "message": "Le service de données est temporairement indisponible.",
        "details": {},
    }
