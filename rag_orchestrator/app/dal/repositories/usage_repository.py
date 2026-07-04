from decimal import Decimal
from typing import Any

import asyncpg


class UsageRepository:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

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

    async def get_active_model_pricing(
        self,
        *,
        provider: str,
        model_name: str,
    ) -> tuple[Decimal, Decimal]:
        query = """
            SELECT
                tarif_modele.prix_input_million,
                tarif_modele.prix_output_million
            FROM tarif_modele
            INNER JOIN modele_llm
                ON modele_llm.id = tarif_modele.modele_id
            WHERE modele_llm.provider = $1
              AND modele_llm.nom = $2
              AND tarif_modele.date_debut <= now()
              AND (
                  tarif_modele.date_fin IS NULL
                  OR tarif_modele.date_fin > now()
              )
            ORDER BY tarif_modele.date_debut DESC
            LIMIT 1
        """

        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(query, provider, model_name)

        if row is None:
            raise ValueError(
                f"No active pricing found for provider={provider} model={model_name}"
            )

        return row["prix_input_million"], row["prix_output_million"]

    async def save_successful_interaction(
        self,
        *,
        session_id: int,
        question: str,
        answer: str | None,
        duration_ms: int,
        provider: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost_eur: float | None,
        retrieved_chunks: list[dict[str, Any]],
    ) -> int:
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                interaction_id = await self._insert_interaction(
                    connection=connection,
                    session_id=session_id,
                    question=question,
                    answer=answer,
                    status="success",
                    duration_ms=duration_ms,
                )

                model_id = await self._upsert_model(
                    connection=connection,
                    provider=provider,
                    model_name=model_name,
                )

                await self._insert_token_usage(
                    connection=connection,
                    interaction_id=interaction_id,
                    model_id=model_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_eur=estimated_cost_eur,
                )

                for rank, chunk in enumerate(retrieved_chunks, start=1):
                    chunk_id = await self._upsert_chunk(
                        connection=connection,
                        chunk=chunk,
                    )
                    await self._insert_interaction_chunk(
                        connection=connection,
                        interaction_id=interaction_id,
                        chunk_id=chunk_id,
                        rank=rank,
                        score=chunk.get("similarity"),
                    )

        return interaction_id

    async def save_failed_interaction(
        self,
        *,
        session_id: int,
        question: str,
        status: str,
        duration_ms: int,
    ) -> int:
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                return await self._insert_interaction(
                    connection=connection,
                    session_id=session_id,
                    question=question,
                    answer=None,
                    status=status,
                    duration_ms=duration_ms,
                )

    async def _insert_interaction(
        self,
        *,
        connection: asyncpg.Connection,
        session_id: int,
        question: str,
        answer: str | None,
        status: str,
        duration_ms: int,
    ) -> int:
        query = """
            INSERT INTO interaction_rag (
                session_id,
                question,
                reponse,
                statut,
                duree_ms
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """

        return await connection.fetchval(
            query,
            session_id,
            question,
            answer,
            status,
            duration_ms,
        )

    async def _upsert_model(
        self,
        *,
        connection: asyncpg.Connection,
        provider: str,
        model_name: str,
    ) -> int:
        query = """
            INSERT INTO modele_llm (provider, nom)
            VALUES ($1, $2)
            ON CONFLICT (provider, nom)
            DO UPDATE SET nom = EXCLUDED.nom
            RETURNING id
        """

        return await connection.fetchval(query, provider, model_name)

    async def _insert_token_usage(
        self,
        *,
        connection: asyncpg.Connection,
        interaction_id: int,
        model_id: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost_eur: float | None,
    ) -> None:
        query = """
            INSERT INTO consommation_tokens (
                interaction_id,
                modele_id,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cout_estime_eur
            )
            VALUES ($1, $2, $3, $4, $5, $6)
        """

        await connection.execute(
            query,
            interaction_id,
            model_id,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            _to_decimal_or_none(estimated_cost_eur),
        )

    async def _upsert_chunk(
        self,
        *,
        connection: asyncpg.Connection,
        chunk: dict[str, Any],
    ) -> int:
        metadata = chunk.get("metadata", {})
        query = """
            INSERT INTO chunk (
                external_chunk_id,
                page_titre,
                page_chemin,
                contenu
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (external_chunk_id)
            DO UPDATE SET
                page_titre = EXCLUDED.page_titre,
                page_chemin = EXCLUDED.page_chemin,
                contenu = EXCLUDED.contenu
            RETURNING id
        """

        return await connection.fetchval(
            query,
            chunk["id"],
            metadata.get("title", ""),
            metadata.get("path", ""),
            chunk.get("document", ""),
        )

    async def _insert_interaction_chunk(
        self,
        *,
        connection: asyncpg.Connection,
        interaction_id: int,
        chunk_id: int,
        rank: int,
        score: float | None,
    ) -> None:
        query = """
            INSERT INTO interaction_rag_chunk (
                interaction_id,
                chunk_id,
                rang,
                score
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (interaction_id, chunk_id) DO NOTHING
        """

        await connection.execute(
            query,
            interaction_id,
            chunk_id,
            rank,
            _to_decimal_or_none(score),
        )


def _to_decimal_or_none(value: float | None) -> Decimal | None:
    if value is None:
        return None

    return Decimal(str(value))
