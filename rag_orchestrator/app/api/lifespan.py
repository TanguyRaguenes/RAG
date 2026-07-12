import logging
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.core.config import load_config
from app.core.metrics import initialize_question_metrics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prépare les ressources applicatives au démarrage puis les libère à l'arrêt du service.

    Args:
        app: Application FastAPI dont l'état contient les ressources partagées du service.

    Raises:
        RuntimeError: Si le traitement rencontre une erreur applicative explicitement propagée.
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

    try:
        logger.info("Opening PostgreSQL connection pool")

        app.state.db_pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=5,
        )

        async with app.state.db_pool.acquire() as connection:
            await connection.execute("SELECT 1")

        logger.info("PostgreSQL connection pool ready")

        yield

    except Exception:
        logger.exception("Failed to initialize PostgreSQL connection pool")
        raise

    finally:
        db_pool = getattr(app.state, "db_pool", None)

        if db_pool is not None:
            logger.info("Closing PostgreSQL connection pool")
            await db_pool.close()
