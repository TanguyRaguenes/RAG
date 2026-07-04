import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_db_pool
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.schemas.quota_schema import (
    QuotaUsageResponse,
    UpdateQuotaRequest,
    UpdateUserPreferencesRequest,
    UserPreferencesResponse,
)
from app.services.usage_tracking_service import (
    get_current_user_preferences,
    get_current_user_quota_usage,
    is_usage_admin,
    list_all_quota_usages,
    update_current_user_preferences,
    update_user_quota,
)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/quota/me", response_model=QuotaUsageResponse)
async def get_my_quota_usage(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
) -> QuotaUsageResponse:
    return await get_current_user_quota_usage(current_user, db_pool)


@router.get("/preferences/me", response_model=UserPreferencesResponse)
async def get_my_preferences(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
) -> UserPreferencesResponse:
    return await get_current_user_preferences(current_user, db_pool)


@router.patch("/preferences/me", response_model=UserPreferencesResponse)
async def update_my_preferences(
    body: UpdateUserPreferencesRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
) -> UserPreferencesResponse:
    try:
        return await update_current_user_preferences(
            current_user,
            db_pool,
            body.theme_preference,
        )
    except ValueError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception


@router.get("/quota/admin/users", response_model=list[QuotaUsageResponse])
async def list_user_quota_usages(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
) -> list[QuotaUsageResponse]:
    _ensure_usage_admin(current_user)

    return await list_all_quota_usages(db_pool)


@router.patch("/quota/admin/users/{user_id}", response_model=QuotaUsageResponse)
async def update_user_quota_usage(
    user_id: str,
    body: UpdateQuotaRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
) -> QuotaUsageResponse:
    _ensure_usage_admin(current_user)

    try:
        return await update_user_quota(
            db_pool=db_pool,
            user_id=user_id,
            max_tokens_per_month=body.max_tokens_par_mois,
            active=body.actif,
        )
    except ValueError as exception:
        raise HTTPException(status_code=404, detail=str(exception)) from exception


def _ensure_usage_admin(current_user: AuthenticatedUser) -> None:
    if is_usage_admin(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Usage administration is restricted to administrators",
    )
