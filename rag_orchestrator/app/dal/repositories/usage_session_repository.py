class UsageSessionRepository:
    async def create_session(self, user_id: str, channel_name: str) -> int:
        """Crée une session d'usage pour regrouper les actions d'une interaction.

        Args:
            user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.
            channel_name: Nom du canal d'usage à créer ou retrouver en base.

        Returns:
            Identifiant de la session d'usage créée en base.

        Raises:
            ValueError: Si une valeur obligatoire est absente ou invalide.
        """
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
        """Marque une session d'usage comme terminée.

        Args:
            session_id: Identifiant de la session d'usage à mettre à jour ou associer à l'interaction.
        """
        query = """
            UPDATE session_usage
            SET finie_le = now()
            WHERE id = $1
        """

        async with self.db_pool.acquire() as connection:
            await connection.execute(query, session_id)
