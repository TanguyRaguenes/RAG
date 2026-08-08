from collections.abc import Mapping
from typing import Any, Protocol

import requests

from app.core.errors import RagApiError
from app.schemas.api import JsonValue


class HttpResponseProtocol(Protocol):
    """Partie d'une réponse HTTP nécessaire au client applicatif."""

    status_code: int

    def json(self) -> object: ...


class HttpClientProtocol(Protocol):
    """Contrat injectable des appels HTTP sortants de l'IHM."""

    def request_json(
        self,
        method: str,
        url: str,
        *,
        timeout: int | None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> JsonValue: ...

    def check_health(self, url: str, *, timeout: int = 5) -> None: ...


class RequestsHttpClient:
    """Adaptateur `requests` qui normalise les erreurs sans exposer leur corps."""

    def request_json(
        self,
        method: str,
        url: str,
        *,
        timeout: int | None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> JsonValue:
        """Exécute une requête et retourne son corps JSON décodé.

        Args:
            method: Méthode HTTP à exécuter.
            url: Endpoint externe cible.
            timeout: Durée maximale de l'appel en secondes, ou aucune limite.
            headers: En-têtes HTTP, dont le bearer token éventuel.
            params: Paramètres de query string.
            data: Corps de formulaire.
            payload: Corps JSON.

        Returns:
            Corps JSON décodé.

        Raises:
            RagApiError: Si le transport, le statut ou le JSON est invalide.
        """
        try:
            response = requests.request(
                method,
                url,
                headers=dict(headers) if headers is not None else None,
                params=dict(params) if params is not None else None,
                data=dict(data) if data is not None else None,
                json=dict(payload) if payload is not None else None,
                timeout=timeout,
            )
        except requests.exceptions.Timeout as exception:
            raise RagApiError(
                "Le service met trop de temps à répondre.",
                {"operation": "http_request"},
                code="service_timeout",
                retryable=True,
            ) from exception
        except requests.exceptions.ConnectionError as exception:
            raise RagApiError(
                "Le service est injoignable pour le moment.",
                {"operation": "http_request"},
                code="service_connection_error",
                retryable=True,
            ) from exception
        except requests.RequestException as exception:
            raise RagApiError(
                "La demande n'a pas pu être envoyée.",
                {
                    "error_type": type(exception).__name__,
                    "operation": "http_request",
                },
                code="service_request_error",
                retryable=True,
            ) from exception

        self._raise_for_status(response)
        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError as exception:
            raise RagApiError(
                "Le service a retourné une réponse illisible.",
                {"operation": "decode_json"},
                code="response_json_error",
            ) from exception

    def check_health(self, url: str, *, timeout: int = 5) -> None:
        """Vérifie directement l'endpoint de santé configuré.

        Args:
            url: URL explicite du healthcheck.
            timeout: Durée maximale de l'appel en secondes.

        Raises:
            RagApiError: Si le service ne répond pas avec un statut 2xx.
        """
        try:
            response = requests.get(url, timeout=timeout)
        except requests.exceptions.Timeout as exception:
            raise RagApiError(
                "Le service met trop de temps à répondre.",
                {"operation": "healthcheck"},
                code="service_timeout",
                retryable=True,
            ) from exception
        except requests.exceptions.ConnectionError as exception:
            raise RagApiError(
                "Le service est injoignable pour le moment.",
                {"operation": "healthcheck"},
                code="service_connection_error",
                retryable=True,
            ) from exception
        except requests.RequestException as exception:
            raise RagApiError(
                "Impossible de vérifier l'état du service.",
                {
                    "error_type": type(exception).__name__,
                    "operation": "healthcheck",
                },
                code="service_request_error",
                retryable=True,
            ) from exception

        self._raise_for_status(response)

    @staticmethod
    def _raise_for_status(response: HttpResponseProtocol) -> None:
        """Transforme un statut non 2xx en message public stable.

        Args:
            response: Réponse dont seul le statut HTTP est consulté.

        Raises:
            RagApiError: Si le statut indique un échec.
        """
        status_code = response.status_code
        if 200 <= status_code < 300:
            return

        if status_code == 401:
            message = "La session a expiré. Reconnecte-toi pour continuer."
        elif status_code == 403:
            message = "Tu n'es pas autorisé à effectuer cette action."
        elif status_code == 429:
            message = "La limite d'utilisation est atteinte pour le moment."
        elif status_code >= 500:
            message = "Le service est momentanément indisponible."
        else:
            message = "Le service n'a pas pu traiter la demande."

        raise RagApiError(
            message,
            details={"status_code": status_code},
            code=f"http_{status_code}",
            retryable=status_code == 429 or status_code >= 500,
        )
