import os

import asyncpg

from app.dal.repositories.usage_repository import UsageRepository
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.services.user_identity_service import build_user_id_from_identifier

MCP_PROVIDER = "KiloCode"
MCP_MODEL = "mcp-retrieval"
DEFAULT_USER_MONTHLY_TOKEN_QUOTA = 100000
QUOTA_EXCEEDED_MESSAGE = (
    "Vous avez consommé votre enveloppe de tokens. "
    "Veuillez vous rapprocher de votre administrateur."
)


class QuotaExceededError(Exception):
    def __init__(self, max_tokens: int, consumed_tokens: int):
        self.max_tokens = max_tokens
        self.consumed_tokens = consumed_tokens
        super().__init__(QUOTA_EXCEEDED_MESSAGE)

async def ensure_usage_user_exists(
    current_user: AuthenticatedUser,
    db_pool: asyncpg.Pool,
) -> str:
    identifier = current_user.email or current_user.sub

    user_id = build_user_id_from_identifier(
        identifier,
        os.environ["USER_HASH_SECRET"],
    )

    usage_repository = UsageRepository(db_pool)
    await usage_repository.upsert_user(user_id)
    await usage_repository.ensure_active_quota_rule(
        user_id=user_id,
        max_tokens_per_month=_get_default_user_monthly_token_quota(),
    )

    return user_id


async def start_usage_session(
    current_user: AuthenticatedUser,
    db_pool: asyncpg.Pool,
    channel: str,
) -> tuple[str, int]:
    user_id = await ensure_usage_user_exists(current_user, db_pool)

    usage_repository = UsageRepository(db_pool)
    session_id = await usage_repository.create_session(user_id, channel)

    return user_id, session_id


async def finish_usage_session(db_pool: asyncpg.Pool, session_id: int) -> None:
    usage_repository = UsageRepository(db_pool)
    await usage_repository.finish_session(session_id)


async def check_user_token_quota(db_pool: asyncpg.Pool, user_id: str) -> None:
    usage_repository = UsageRepository(db_pool)
    max_tokens, consumed_tokens = await usage_repository.get_active_quota_usage(user_id)

    if consumed_tokens >= max_tokens:
        raise QuotaExceededError(max_tokens, consumed_tokens)


async def save_successful_question_usage(
    *,
    db_pool: asyncpg.Pool,
    session_id: int,
    question: str,
    llm_provider: str,
    answer: AskQuestionResponseBase,
    duration_ms: int,
) -> int:
    usage_repository = UsageRepository(db_pool)

    return await usage_repository.save_successful_interaction(
        session_id=session_id,
        question=question,
        answer=answer.llm_response,
        duration_ms=duration_ms,
        provider=llm_provider,
        model_name=answer.model,
        prompt_tokens=answer.input_tokens,
        completion_tokens=answer.output_tokens,
        total_tokens=answer.total_tokens,
        estimated_cost_eur=answer.cost,
        retrieved_chunks=answer.retrieved_chunks,
    )


async def save_failed_question_usage(
    *,
    db_pool: asyncpg.Pool,
    session_id: int,
    question: str,
    status: str,
    duration_ms: int,
) -> int:
    usage_repository = UsageRepository(db_pool)

    return await usage_repository.save_failed_interaction(
        session_id=session_id,
        question=question,
        status=status,
        duration_ms=duration_ms,
    )


async def save_retrieval_usage(
    *,
    db_pool: asyncpg.Pool,
    session_id: int,
    question: str,
    retrieved_chunks: list[dict],
    duration_ms: int,
) -> int:
    usage_repository = UsageRepository(db_pool)

    return await usage_repository.save_successful_interaction(
        session_id=session_id,
        question=question,
        answer=None,
        duration_ms=duration_ms,
        provider=MCP_PROVIDER,
        model_name=MCP_MODEL,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        estimated_cost_eur=0.0,
        retrieved_chunks=retrieved_chunks,
    )


def _get_default_user_monthly_token_quota() -> int:
    raw_value = os.getenv(
        "DEFAULT_USER_MONTHLY_TOKEN_QUOTA",
        str(DEFAULT_USER_MONTHLY_TOKEN_QUOTA),
    )

    try:
        max_tokens = int(raw_value)
    except ValueError as exception:
        raise ValueError("DEFAULT_USER_MONTHLY_TOKEN_QUOTA must be an integer") from exception

    if max_tokens <= 0:
        raise ValueError("DEFAULT_USER_MONTHLY_TOKEN_QUOTA must be greater than 0")

    return max_tokens
