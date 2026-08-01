from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

import asyncpg

from app.core.exceptions import DatabaseError


class BaseUsageRepository:
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        """Conserve le pool PostgreSQL partagé par les repositories d'usage.

        Args:
            db_pool: Pool de connexions PostgreSQL utilisé pour lire ou écrire les données d'usage.
        """
        self.db_pool = db_pool

    @asynccontextmanager
    async def _acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Fournit une connexion et traduit uniquement les erreurs asyncpg.

        Yields:
            Connexion PostgreSQL acquise depuis le pool partagé.

        Raises:
            DatabaseError: Si asyncpg échoue pendant l'acquisition ou l'opération SQL.
        """
        try:
            async with self.db_pool.acquire() as connection:
                yield connection
        except asyncpg.PostgresError as exception:
            raise DatabaseError("PostgreSQL repository operation failed") from exception


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
