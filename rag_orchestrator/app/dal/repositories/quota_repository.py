import asyncpg


class QuotaRepository:
    async def ensure_default_quota_rule(
        self,
        *,
        user_id: str,
        max_tokens_per_month: int,
    ) -> None:
        query = """
            INSERT INTO quota_utilisateur (
                utilisateur_id,
                max_tokens_par_mois,
                actif,
                date_debut,
                date_fin
            )
            SELECT
                $1,
                $2,
                true,
                now(),
                NULL
            WHERE NOT EXISTS (
                SELECT 1
                FROM quota_utilisateur
                WHERE utilisateur_id = $1
            )
            ON CONFLICT DO NOTHING
        """

        async with self.db_pool.acquire() as connection:
            await connection.execute(query, user_id, max_tokens_per_month)

    async def get_active_quota_usage(self, user_id: str) -> tuple[int, int, bool]:
        query = """
            WITH active_quota AS (
                SELECT
                    id,
                    utilisateur_id,
                    max_tokens_par_mois,
                    actif,
                    date_debut,
                    date_fin
                FROM quota_utilisateur
                WHERE utilisateur_id = $1
                  AND date_debut <= now()
                  AND (date_fin IS NULL OR date_fin > now())
                ORDER BY date_debut DESC
                LIMIT 1
            ), current_month AS (
                SELECT
                    date_trunc('month', now()) AS date_debut,
                    date_trunc('month', now()) + interval '1 month' AS date_fin
            )
            SELECT
                active_quota.max_tokens_par_mois,
                active_quota.actif,
                COALESCE(SUM(consommation_tokens.total_tokens), 0)::bigint AS consumed_tokens
            FROM active_quota
            CROSS JOIN current_month
            LEFT JOIN session_usage
                ON session_usage.utilisateur_id = active_quota.utilisateur_id
            LEFT JOIN interaction_rag
                ON interaction_rag.session_id = session_usage.id
               AND interaction_rag.cree_le >= current_month.date_debut
               AND interaction_rag.cree_le < current_month.date_fin
            LEFT JOIN consommation_tokens
                ON consommation_tokens.interaction_id = interaction_rag.id
            GROUP BY active_quota.max_tokens_par_mois, active_quota.actif
        """

        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(query, user_id)

        if row is None:
            raise ValueError("No active quota found for user")

        return row["max_tokens_par_mois"], row["consumed_tokens"], row["actif"]

    async def get_quota_usage_details(self, user_id: str) -> asyncpg.Record:
        query = """
            WITH current_month AS (
                SELECT
                    date_trunc('month', now()) AS date_debut,
                    date_trunc('month', now()) + interval '1 month' AS date_fin
            )
            SELECT
                utilisateur.email,
                quota_utilisateur.utilisateur_id,
                quota_utilisateur.max_tokens_par_mois,
                quota_utilisateur.actif,
                quota_utilisateur.date_debut,
                quota_utilisateur.date_fin,
                COALESCE(SUM(consommation_tokens.total_tokens), 0)::bigint AS consumed_tokens
            FROM quota_utilisateur
            INNER JOIN utilisateur
                ON utilisateur.id = quota_utilisateur.utilisateur_id
            CROSS JOIN current_month
            LEFT JOIN session_usage
                ON session_usage.utilisateur_id = quota_utilisateur.utilisateur_id
            LEFT JOIN interaction_rag
                ON interaction_rag.session_id = session_usage.id
               AND interaction_rag.cree_le >= current_month.date_debut
               AND interaction_rag.cree_le < current_month.date_fin
            LEFT JOIN consommation_tokens
                ON consommation_tokens.interaction_id = interaction_rag.id
            WHERE quota_utilisateur.utilisateur_id = $1
              AND quota_utilisateur.date_debut <= now()
              AND (
                  quota_utilisateur.date_fin IS NULL
                  OR quota_utilisateur.date_fin > now()
              )
            GROUP BY
                utilisateur.email,
                quota_utilisateur.utilisateur_id,
                quota_utilisateur.max_tokens_par_mois,
                quota_utilisateur.actif,
                quota_utilisateur.date_debut,
                quota_utilisateur.date_fin
            ORDER BY quota_utilisateur.date_debut DESC
            LIMIT 1
        """

        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(query, user_id)

        if row is None:
            raise ValueError("No quota found for user")

        return row

    async def list_quota_usages(self) -> list[asyncpg.Record]:
        query = """
            WITH current_month AS (
                SELECT
                    date_trunc('month', now()) AS date_debut,
                    date_trunc('month', now()) + interval '1 month' AS date_fin
            )
            SELECT
                utilisateur.id AS utilisateur_id,
                utilisateur.email,
                quota_utilisateur.max_tokens_par_mois,
                quota_utilisateur.actif,
                quota_utilisateur.date_debut,
                quota_utilisateur.date_fin,
                COALESCE(SUM(consommation_tokens.total_tokens), 0)::bigint AS consumed_tokens
            FROM utilisateur
            LEFT JOIN quota_utilisateur
                ON quota_utilisateur.utilisateur_id = utilisateur.id
            CROSS JOIN current_month
            LEFT JOIN session_usage
                ON session_usage.utilisateur_id = utilisateur.id
            LEFT JOIN interaction_rag
                ON interaction_rag.session_id = session_usage.id
               AND interaction_rag.cree_le >= current_month.date_debut
               AND interaction_rag.cree_le < current_month.date_fin
            LEFT JOIN consommation_tokens
                ON consommation_tokens.interaction_id = interaction_rag.id
            GROUP BY
                utilisateur.id,
                utilisateur.email,
                quota_utilisateur.max_tokens_par_mois,
                quota_utilisateur.actif,
                quota_utilisateur.date_debut,
                quota_utilisateur.date_fin
            ORDER BY consumed_tokens DESC, utilisateur.id
        """

        async with self.db_pool.acquire() as connection:
            return await connection.fetch(query)

    async def update_quota_rule(
        self,
        *,
        user_id: str,
        max_tokens_per_month: int,
        active: bool,
    ) -> None:
        query = """
            UPDATE quota_utilisateur
            SET
                max_tokens_par_mois = $2,
                actif = $3,
                date_fin = NULL
            WHERE utilisateur_id = $1
        """

        async with self.db_pool.acquire() as connection:
            result = await connection.execute(
                query,
                user_id,
                max_tokens_per_month,
                active,
            )

        if result == "UPDATE 0":
            raise ValueError("Unknown user quota")
