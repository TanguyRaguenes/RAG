from app.core.errors import RagApiError
from app.dal.clients.http_client import HttpClientProtocol
from app.schemas.api import (
    ResponseContractError,
    TokenResponse,
    validate_token_response,
)


class OidcClient:
    """Client technique de l'endpoint token Pocket ID."""

    def __init__(self, http_client: HttpClientProtocol) -> None:
        """Injecte le transport HTTP utilisé pour l'échange OAuth.

        Args:
            http_client: Adaptateur HTTP injectable.
        """
        self._http_client = http_client

    def exchange_code(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> TokenResponse:
        """Échange un code d'autorisation contre les tokens Pocket ID.

        Args:
            token_url: Endpoint token OIDC.
            client_id: Identifiant public de l'application Streamlit.
            client_secret: Secret du client confidentiel.
            code: Code à usage unique retourné par Pocket ID.
            redirect_uri: URI identique à celle de la demande d'autorisation.

        Returns:
            DTO de tokens validé comme objet JSON.

        Raises:
            RagApiError: Si Pocket ID renvoie un format inattendu.
        """
        payload = self._http_client.request_json(
            "POST",
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        try:
            return validate_token_response(payload)
        except ResponseContractError as exception:
            raise RagApiError(
                "Pocket ID a retourné une réponse inattendue.",
                {"contract": "oidc_token", "dependency": "pocket_id"},
                code="oidc_response_contract_error",
            ) from exception
