import os

import asyncpg

from app.dal.repositories.usage_repository import UsageRepository
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.services.user_identity_service import build_user_id_from_email


async def ensure_usage_user_exists(
    current_user: AuthenticatedUser,
    db_pool: asyncpg.Pool,
) -> str:
    if current_user.email is None:
        raise ValueError("Authenticated user email is required for usage tracking")

    user_id = build_user_id_from_email(
        current_user.email,
        os.environ["USER_HASH_SECRET"],
    )

    usage_repository = UsageRepository(db_pool)
    await usage_repository.upsert_user(user_id)

    return user_id
