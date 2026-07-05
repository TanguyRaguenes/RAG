class UsageSessionRepository:
    async def create_session(self, user_id: str, channel_name: str) -> int:
        query = """
            INSERT INTO session_usage (utilisateur_id, canal_id)
            SELECT $1, id
            FROM canal
            WHERE nom = $2
            RETURNING id
        """

        async with self.db_pool.acquire() as connection:
            session_id = await connection.fetchval(query, user_id, channel_name)

        if session_id is None:
            raise ValueError(f"Unknown usage channel: {channel_name}")

        return session_id

    async def finish_session(self, session_id: int) -> None:
        query = """
            UPDATE session_usage
            SET finie_le = now()
            WHERE id = $1
        """

        async with self.db_pool.acquire() as connection:
            await connection.execute(query, session_id)
