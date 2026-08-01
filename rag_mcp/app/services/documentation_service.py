import json
from typing import Protocol

from app.schemas.rag_response import RetrievedChunksResponse


class RagClientProtocol(Protocol):
    """Contrat du client injecté dans le service documentaire."""

    async def retrieve_documentation_chunks(
        self,
        question: str,
        access_token: str,
    ) -> RetrievedChunksResponse: ...


class DocumentationService:
    """Orchestre la recherche puis formate la réponse publique de l'outil MCP."""

    def __init__(self, rag_client: RagClientProtocol) -> None:
        """Injecte le client RAG utilisé pour la recherche.

        Args:
            rag_client: Client interservice retournant un DTO validé.
        """
        self._rag_client = rag_client

    async def answer(self, question: str, access_token: str) -> str:
        """Recherche les chunks et les sérialise pour l'appelant MCP.

        Args:
            question: Question documentaire reçue par l'outil MCP.
            access_token: Bearer token de l'utilisateur courant.

        Returns:
            JSON lisible des chunks ou message indiquant l'absence de résultat.
        """
        response = await self._rag_client.retrieve_documentation_chunks(
            question,
            access_token,
        )
        if not response.retrieved_chunks:
            return "Aucune information trouvée."

        return json.dumps(response.retrieved_chunks, ensure_ascii=False, indent=2)
