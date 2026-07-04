import asyncpg


class UsageRepository:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def upsert_user(self, user_id: str) -> None:
        query = """
            INSERT INTO utilisateur (id)
            VALUES ($1)
            ON CONFLICT (id) DO NOTHING
        """

        async with self.db_pool.acquire() as connection:
            await connection.execute(query, user_id)
