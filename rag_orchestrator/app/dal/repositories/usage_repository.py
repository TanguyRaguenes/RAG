from app.dal.repositories.base_usage_repository import (
    BaseUsageRepository,
    _to_decimal_or_none,
)
from app.dal.repositories.feedback_repository import FeedbackRepository
from app.dal.repositories.interaction_repository import InteractionRepository
from app.dal.repositories.model_pricing_repository import ModelPricingRepository
from app.dal.repositories.quota_repository import QuotaRepository
from app.dal.repositories.usage_session_repository import UsageSessionRepository
from app.dal.repositories.usage_user_repository import UsageUserRepository


class UsageRepository(
    BaseUsageRepository,
    UsageUserRepository,
    QuotaRepository,
    UsageSessionRepository,
    ModelPricingRepository,
    InteractionRepository,
    FeedbackRepository,
):
    """Façade compatible regroupant les repositories liés au suivi d'usage."""


__all__ = ["UsageRepository", "_to_decimal_or_none"]
