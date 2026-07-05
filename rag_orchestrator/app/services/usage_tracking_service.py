import os
import json
from datetime import date
from typing import Iterable

import asyncpg

from app.dal.repositories.usage_repository import UsageRepository
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.schemas.feedback_schema import (
    AdminInteractionFeedbackResponse,
    FeedbackResponse,
)
from app.schemas.quota_schema import QuotaUsageResponse, UserPreferencesResponse
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


class QuotaInactiveError(Exception):
    def __init__(self):
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
    await usage_repository.upsert_user(user_id, _normalize_optional_email(current_user.email))
    await usage_repository.ensure_default_quota_rule(
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
    max_tokens, consumed_tokens, active = await usage_repository.get_active_quota_usage(user_id)

    if not active:
        raise QuotaInactiveError()

    if consumed_tokens >= max_tokens:
        raise QuotaExceededError(max_tokens, consumed_tokens)


async def get_current_user_quota_usage(
    current_user: AuthenticatedUser,
    db_pool: asyncpg.Pool,
) -> QuotaUsageResponse:
    user_id = await ensure_usage_user_exists(current_user, db_pool)
    usage_repository = UsageRepository(db_pool)
    row = await usage_repository.get_quota_usage_details(user_id)

    return _quota_row_to_response(row)


async def list_all_quota_usages(db_pool: asyncpg.Pool) -> list[QuotaUsageResponse]:
    usage_repository = UsageRepository(db_pool)
    rows = await usage_repository.list_quota_usages()

    return [_quota_row_to_response(row) for row in rows if row["max_tokens_par_mois"]]


async def update_user_quota(
    *,
    db_pool: asyncpg.Pool,
    user_id: str,
    max_tokens_per_month: int,
    active: bool,
) -> QuotaUsageResponse:
    usage_repository = UsageRepository(db_pool)
    await usage_repository.update_quota_rule(
        user_id=user_id,
        max_tokens_per_month=max_tokens_per_month,
        active=active,
    )
    row = await usage_repository.get_quota_usage_details(user_id)

    return _quota_row_to_response(row)


async def get_current_user_preferences(
    current_user: AuthenticatedUser,
    db_pool: asyncpg.Pool,
) -> UserPreferencesResponse:
    user_id = await ensure_usage_user_exists(current_user, db_pool)
    usage_repository = UsageRepository(db_pool)
    theme_preference = await usage_repository.get_user_theme_preference(user_id)

    return UserPreferencesResponse(theme_preference=theme_preference)


async def update_current_user_preferences(
    current_user: AuthenticatedUser,
    db_pool: asyncpg.Pool,
    theme_preference: str,
) -> UserPreferencesResponse:
    if theme_preference not in {"Sombre", "Clair"}:
        raise ValueError("Unknown theme preference")

    user_id = await ensure_usage_user_exists(current_user, db_pool)
    usage_repository = UsageRepository(db_pool)
    await usage_repository.update_user_theme_preference(
        user_id=user_id,
        theme_preference=theme_preference,
    )

    return UserPreferencesResponse(theme_preference=theme_preference)


async def save_current_user_feedback(
    current_user: AuthenticatedUser,
    db_pool: asyncpg.Pool,
    interaction_id: int,
    note: int,
    comment: str | None,
) -> FeedbackResponse:
    user_id = await ensure_usage_user_exists(current_user, db_pool)
    usage_repository = UsageRepository(db_pool)
    normalized_comment = _normalize_optional_comment(comment)

    await usage_repository.upsert_feedback(
        interaction_id=interaction_id,
        user_id=user_id,
        note=note,
        comment=normalized_comment,
    )

    return FeedbackResponse(
        interaction_id=interaction_id,
        note=note,
        commentaire=normalized_comment,
    )


async def list_admin_interaction_feedbacks(
    db_pool: asyncpg.Pool,
    start_date: date,
    end_date: date,
) -> list[AdminInteractionFeedbackResponse]:
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date")

    usage_repository = UsageRepository(db_pool)
    rows = await usage_repository.list_interaction_feedbacks(
        start_date=start_date,
        end_date=end_date,
    )

    return [
        AdminInteractionFeedbackResponse(
            interaction_id=row["interaction_id"],
            cree_le=row["cree_le"],
            question=row["question"],
            reponse=row["reponse"],
            note=row["note"],
            commentaire=row["commentaire"],
            chunks=_decode_chunks(row["chunks"]),
        )
        for row in rows
    ]


def is_usage_admin(current_user: AuthenticatedUser) -> bool:
    return bool(_normalize_groups(current_user.groups) & _get_admin_groups())


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


def _quota_row_to_response(row) -> QuotaUsageResponse:
    max_tokens = int(row["max_tokens_par_mois"])
    consumed_tokens = int(row["consumed_tokens"])
    remaining_tokens = max(max_tokens - consumed_tokens, 0)
    usage_ratio = consumed_tokens / max_tokens if max_tokens > 0 else 0.0

    return QuotaUsageResponse(
        utilisateur_id=row["utilisateur_id"],
        email=row["email"],
        max_tokens_par_mois=max_tokens,
        consumed_tokens=consumed_tokens,
        remaining_tokens=remaining_tokens,
        usage_ratio=min(usage_ratio, 1.0),
        actif=bool(row["actif"]),
        date_debut=row["date_debut"],
        date_fin=row["date_fin"],
    )


def _get_admin_groups() -> set[str]:
    raw_groups = os.getenv("RAG_USAGE_ADMIN_GROUPS", "admin,admins,rag-admin")

    return _normalize_groups(raw_groups.split(","))


def _normalize_groups(groups: Iterable[str]) -> set[str]:
    return {group.strip().lower() for group in groups if group.strip()}


def _normalize_optional_email(email: str | None) -> str | None:
    if email is None:
        return None

    normalized_email = email.strip().lower()

    return normalized_email or None


def _normalize_optional_comment(comment: str | None) -> str | None:
    if comment is None:
        return None

    normalized_comment = comment.strip()

    return normalized_comment or None


def _decode_chunks(raw_chunks) -> list[dict]:
    if isinstance(raw_chunks, list):
        return raw_chunks

    if isinstance(raw_chunks, str):
        try:
            loaded_chunks = json.loads(raw_chunks)
        except json.JSONDecodeError:
            return []

        return loaded_chunks if isinstance(loaded_chunks, list) else []

    return []
