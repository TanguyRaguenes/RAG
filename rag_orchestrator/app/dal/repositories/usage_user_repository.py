class UsageUserRepository:
    async def upsert_user(
        self,
        *,
        user_id: str,
        issuer: str | None,
        subject: str | None,
        email: str | None,
        display_name: str | None,
        preferred_username: str | None,
    ) -> None:
        """Insère ou met à jour les informations connues d'un utilisateur d'usage.

        Args:
            user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.
            issuer: Émetteur OIDC associé à l'identité utilisateur.
            subject: Claim `sub` stable de l'utilisateur chez l'émetteur OIDC.
            email: Adresse e-mail utilisée pour l'affichage administrateur.
            display_name: Nom lisible de l'utilisateur si fourni par Pocket ID.
            preferred_username: Identifiant lisible de l'utilisateur si fourni par Pocket ID.
        """
        query = """
            INSERT INTO utilisateur (
                id,
                issuer,
                subject,
                email,
                display_name,
                preferred_username
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id)
            DO UPDATE SET
                issuer = COALESCE(EXCLUDED.issuer, utilisateur.issuer),
                subject = COALESCE(EXCLUDED.subject, utilisateur.subject),
                email = COALESCE(EXCLUDED.email, utilisateur.email),
                display_name = COALESCE(EXCLUDED.display_name, utilisateur.display_name),
                preferred_username = COALESCE(
                    EXCLUDED.preferred_username,
                    utilisateur.preferred_username
                )
        """

        async with self._acquire() as connection:
            await connection.execute(
                query,
                user_id,
                issuer,
                subject,
                email,
                display_name,
                preferred_username,
            )
