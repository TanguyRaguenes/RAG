import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.core.config import load_config
from app.core.exceptions import DatabaseError
from app.core.metrics import initialize_question_metrics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prépare les ressources applicatives au démarrage puis les libère à l'arrêt du service.

    Args:
        app: Application FastAPI dont l'état contient les ressources partagées du service.

    Raises:
        RuntimeError: Si le secret de pseudonymisation est vide.
        DatabaseError: Si le pool PostgreSQL ne peut pas être initialisé.
    """
    app.state.config = load_config()
    initialize_question_metrics(
        provider=app.state.config["llm"]["api"]["provider"],
        model=app.state.config["llm"]["api"]["model"],
    )

    database_url = os.environ["DATABASE_URL"]
    user_hash_secret = os.environ["USER_HASH_SECRET"]

    if not user_hash_secret.strip():
        raise RuntimeError("USER_HASH_SECRET must not be empty")

    logger.info("Opening PostgreSQL connection pool")
    db_pool: asyncpg.Pool | None = None
    try:
        db_pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=5,
        )

        async with db_pool.acquire() as connection:
            await connection.execute("SELECT 1")
    except (asyncpg.PostgresError, OSError) as exception:
        if db_pool is not None:
            await db_pool.close()
        raise DatabaseError("PostgreSQL pool initialization failed") from exception

    app.state.db_pool = db_pool
    logger.info("PostgreSQL connection pool ready")
    try:
        yield
    finally:
        logger.info("Closing PostgreSQL connection pool")
        await db_pool.close()
