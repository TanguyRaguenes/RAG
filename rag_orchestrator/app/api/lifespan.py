import logging
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.core.config import load_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config()

    database_url = os.environ["DATABASE_URL"]

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