class UsageUserRepository:
    async def upsert_user(self, user_id: str, email: str | None) -> None:
        """Insère ou met à jour les informations connues d'un utilisateur d'usage.

        Args:
            user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.
            email: Adresse e-mail utilisée pour identifier l'utilisateur sans l'exposer inutilement.
        """
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
        """Récupère la préférence de thème enregistrée pour un utilisateur.

        Args:
            user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.

        Returns:
            Thème préféré enregistré pour l'utilisateur, ou le thème par défaut.

        Raises:
            ValueError: Si une valeur obligatoire est absente ou invalide.
        """
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
        """Enregistre la préférence de thème d'un utilisateur.

        Args:
            user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.
            theme_preference: Préférence de thème choisie par l'utilisateur.

        Raises:
            ValueError: Si une valeur obligatoire est absente ou invalide.
        """
        query = """
            UPDATE utilisateur
            SET theme_preference = $2
            WHERE id = $1
        """

        async with self.db_pool.acquire() as connection:
            result = await connection.execute(query, user_id, theme_preference)

        if result == "UPDATE 0":
            raise ValueError("Unknown user")
