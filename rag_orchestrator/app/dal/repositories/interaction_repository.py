from typing import Any

import asyncpg

from app.dal.repositories.base_usage_repository import _to_decimal_or_none


class InteractionRepository:
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
