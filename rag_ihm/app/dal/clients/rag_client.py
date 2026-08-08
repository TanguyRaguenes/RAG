from collections.abc import Mapping
from typing import Any

from app.dal.clients.http_client import HttpClientProtocol
from app.schemas.api import JsonValue


class RagClient:
    """Client technique des APIs orchestrator et evaluator."""

    def __init__(self, http_client: HttpClientProtocol) -> None:
        """Injecte le transport commun aux APIs RAG.

        Args:
            http_client: Adaptateur HTTP injectable.
        """
        self._http_client = http_client

    def check_health(self, url: str) -> None:
        """Appelle l'URL de santé explicite d'un service.

        Args:
            url: Endpoint de santé complet, sans transformation.
        """
        self._http_client.check_health(url)

    def request_json(
        self,
        method: str,
        url: str,
        *,
        timeout: int | None,
        access_token: str | None = None,
        params: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> JsonValue:
        """Envoie une requête JSON éventuellement authentifiée.

        Args:
            method: Méthode HTTP cible.
            url: Endpoint API complet.
            timeout: Durée maximale de l'appel, ou aucune limite.
            access_token: Bearer token à transmettre s'il est fourni.
            params: Paramètres de query string.
            payload: Corps JSON.

        Returns:
            Corps JSON décodé par le transport.
        """
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
        return self._http_client.request_json(
            method,
            url,
            timeout=timeout,
            headers=headers,
            params=params,
            payload=payload,
        )
