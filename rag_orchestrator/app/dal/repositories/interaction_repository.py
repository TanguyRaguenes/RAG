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
        """Persiste une interaction réussie avec ses métadonnées, tokens et chunks.

        Args:
            session_id: Identifiant de la session d'usage à mettre à jour ou associer à l'interaction.
            question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
            answer: Réponse RAG générée pour l'utilisateur, ou `None` si aucune réponse n'est disponible.
            duration_ms: Durée de traitement de l'interaction exprimée en millisecondes.
            provider: Provider LLM ou service externe concerné.
            model_name: Nom du modèle LLM référencé par l'usage ou la tarification.
            prompt_tokens: Nombre de tokens consommés par le prompt envoyé au modèle.
            completion_tokens: Nombre de tokens générés par le modèle dans la réponse.
            total_tokens: Nombre total de tokens consommés par l'appel LLM.
            estimated_cost_eur: Coût estimé de l'appel LLM en euros.
            retrieved_chunks: Chunks retournés par le retriever ou l'orchestrator.

        Returns:
            Identifiant de l'interaction RAG créée en base.
        """
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
        """Persiste une interaction échouée avec son statut et sa durée.

        Args:
            session_id: Identifiant de la session d'usage à mettre à jour ou associer à l'interaction.
            question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
            status: Statut fonctionnel ou technique de l'opération.
            duration_ms: Durée de traitement de l'interaction exprimée en millisecondes.

        Returns:
            Identifiant de l'interaction échouée créée en base.
        """
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
        """Insère la ligne principale d'une interaction dans la base d'usage.

        Args:
            connection: Connexion PostgreSQL transactionnelle utilisée pour grouper les écritures.
            session_id: Identifiant de la session d'usage à mettre à jour ou associer à l'interaction.
            question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
            answer: Réponse RAG générée pour l'utilisateur, ou `None` en cas d'échec ou de retrieval seul.
            status: Statut fonctionnel ou technique de l'opération.
            duration_ms: Durée de traitement de l'interaction exprimée en millisecondes.

        Returns:
            Identifiant de la ligne `interaction_rag` insérée.
        """
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
        """Insère ou récupère le modèle LLM référencé par une interaction.

        Args:
            connection: Connexion PostgreSQL transactionnelle utilisée pour grouper les écritures.
            provider: Provider LLM ou service externe concerné.
            model_name: Nom du modèle LLM référencé par l'usage ou la tarification.

        Returns:
            Identifiant du modèle existant ou nouvellement inséré.
        """
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
        """Insère les compteurs de tokens et le coût d'une interaction.

        Args:
            connection: Connexion PostgreSQL transactionnelle utilisée pour grouper les écritures.
            interaction_id: Identifiant de l'interaction RAG concernée.
            model_id: Identifiant interne du modèle LLM associé à l'interaction.
            prompt_tokens: Nombre de tokens consommés par le prompt envoyé au modèle.
            completion_tokens: Nombre de tokens générés par le modèle dans la réponse.
            total_tokens: Nombre total de tokens consommés par l'appel LLM.
            estimated_cost_eur: Coût estimé de l'appel LLM en euros.
        """
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
        """Insère ou récupère un chunk référencé par une interaction.

        Args:
            connection: Connexion PostgreSQL transactionnelle utilisée pour grouper les écritures.
            chunk: Chunk documentaire à formater, afficher ou persister.

        Returns:
            Identifiant du chunk existant ou nouvellement inséré.
        """
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
        """Associe un chunk récupéré à une interaction RAG.

        Args:
            connection: Connexion PostgreSQL transactionnelle utilisée pour grouper les écritures.
            interaction_id: Identifiant de l'interaction RAG concernée.
            chunk_id: Identifiant du chunk vectoriel associé à l'interaction.
            rank: Position du chunk dans les résultats présentés à l'utilisateur.
            score: Score de similarité ou de reranking associé au chunk.
        """
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
