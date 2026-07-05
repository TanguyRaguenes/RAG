from datetime import date

import asyncpg


class FeedbackRepository:
    async def upsert_feedback(
        self,
        *,
        interaction_id: int,
        user_id: str,
        note: int,
        comment: str | None,
    ) -> None:
        query = """
            INSERT INTO avis (interaction_id, note, commentaire)
            SELECT $1, $3, $4
            WHERE EXISTS (
                SELECT 1
                FROM interaction_rag
                INNER JOIN session_usage
                    ON session_usage.id = interaction_rag.session_id
                WHERE interaction_rag.id = $1
                  AND session_usage.utilisateur_id = $2
                  AND interaction_rag.statut = 'success'
            )
            ON CONFLICT (interaction_id)
            DO UPDATE SET
                note = EXCLUDED.note,
                commentaire = EXCLUDED.commentaire
            RETURNING id
        """

        async with self.db_pool.acquire() as connection:
            feedback_id = await connection.fetchval(
                query,
                interaction_id,
                user_id,
                note,
                comment,
            )

        if feedback_id is None:
            raise ValueError("Unknown interaction for current user")

    async def list_interaction_feedbacks(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[asyncpg.Record]:
        query = """
            SELECT
                interaction_rag.id AS interaction_id,
                interaction_rag.cree_le,
                interaction_rag.question,
                interaction_rag.reponse,
                avis.note,
                avis.commentaire,
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'rang', interaction_rag_chunk.rang,
                            'score', interaction_rag_chunk.score,
                            'titre', chunk.page_titre,
                            'chemin', chunk.page_chemin,
                            'contenu', chunk.contenu
                        )
                        ORDER BY interaction_rag_chunk.rang
                    ) FILTER (WHERE chunk.id IS NOT NULL),
                    '[]'::jsonb
                ) AS chunks
            FROM interaction_rag
            LEFT JOIN avis
                ON avis.interaction_id = interaction_rag.id
            LEFT JOIN interaction_rag_chunk
                ON interaction_rag_chunk.interaction_id = interaction_rag.id
            LEFT JOIN chunk
                ON chunk.id = interaction_rag_chunk.chunk_id
            WHERE interaction_rag.cree_le >= $1::date
              AND interaction_rag.cree_le < ($2::date + interval '1 day')
              AND interaction_rag.statut = 'success'
            GROUP BY
                interaction_rag.id,
                interaction_rag.cree_le,
                interaction_rag.question,
                interaction_rag.reponse,
                avis.note,
                avis.commentaire
            ORDER BY interaction_rag.cree_le DESC
        """

        async with self.db_pool.acquire() as connection:
            return await connection.fetch(query, start_date, end_date)
