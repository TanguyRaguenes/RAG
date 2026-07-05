from decimal import Decimal


class ModelPricingRepository:
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
