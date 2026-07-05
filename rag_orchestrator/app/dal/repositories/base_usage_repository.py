from decimal import Decimal

import asyncpg


class BaseUsageRepository:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool


def _to_decimal_or_none(value: float | None) -> Decimal | None:
    if value is None:
        return None

    return Decimal(str(value))
