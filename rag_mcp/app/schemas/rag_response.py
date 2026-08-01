from dataclasses import dataclass
from typing import Any

from app.core.errors import McpResponseContractError


@dataclass(frozen=True)
class RetrievedChunksResponse:
    """DTO des extraits documentaires retournés par l'orchestrator."""

    retrieved_chunks: tuple[dict[str, Any], ...]

    @classmethod
    def from_payload(cls, payload: object) -> "RetrievedChunksResponse":
        """Valide le type minimal de la réponse interservice.

        Args:
            payload: Corps JSON décodé reçu de l'orchestrator.

        Returns:
            DTO immuable contenant uniquement les chunks valides.

        Raises:
            McpResponseContractError: Si la structure est incompatible.
        """
        if not isinstance(payload, dict):
            raise McpResponseContractError(
                safe_details={"dependency": "rag_orchestrator"}
            )

        if "retrieved_chunks" not in payload:
            raise McpResponseContractError(
                safe_details={"dependency": "rag_orchestrator"}
            )

        chunks = payload["retrieved_chunks"]
        if not isinstance(chunks, list) or not all(
            isinstance(chunk, dict) for chunk in chunks
        ):
            raise McpResponseContractError(
                safe_details={"dependency": "rag_orchestrator"}
            )

        return cls(retrieved_chunks=tuple(chunks))
