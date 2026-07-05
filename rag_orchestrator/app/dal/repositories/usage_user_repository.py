class UsageUserRepository:
    async def upsert_user(self, user_id: str, email: str | None) -> None:
        query = """
            INSERT INTO utilisateur (id, email)
            VALUES ($1, $2)
            ON CONFLICT (id)
            DO UPDATE SET
                email = COALESCE(EXCLUDED.email, utilisateur.email)
        """

        async with self.db_pool.acquire() as connection:
            await connection.execute(query, user_id, email)

    async def get_user_theme_preference(self, user_id: str) -> str:
        query = """
            SELECT theme_preference
            FROM utilisateur
            WHERE id = $1
        """

        async with self.db_pool.acquire() as connection:
            theme_preference = await connection.fetchval(query, user_id)

        if theme_preference is None:
            raise ValueError("Unknown user")

        return theme_preference

    async def update_user_theme_preference(
        self,
        *,
        user_id: str,
        theme_preference: str,
    ) -> None:
        query = """
            UPDATE utilisateur
            SET theme_preference = $2
            WHERE id = $1
        """

        async with self.db_pool.acquire() as connection:
            result = await connection.execute(query, user_id, theme_preference)

        if result == "UPDATE 0":
            raise ValueError("Unknown user")
