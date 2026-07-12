from decimal import Decimal

import asyncpg


class BaseUsageRepository:
    def __init__(self, db_pool: asyncpg.Pool):
        """Conserve le pool PostgreSQL partagé par les repositories d'usage.

        Args:
            db_pool: Pool de connexions PostgreSQL utilisé pour lire ou écrire les données d'usage.
        """
        self.db_pool = db_pool


def _to_decimal_or_none(value: float | None) -> Decimal | None:
    """Convertit une valeur numérique optionnelle en Decimal pour les calculs de coût.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Valeur convertie en Decimal, ou `None` si la valeur d'entrée est absente.
    """
    if value is None:
        return None

    return Decimal(str(value))
