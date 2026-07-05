import os
from typing import Any

import httpx

from app.core.exceptions import EvaluatorClientError


async def ask_question(question: str) -> dict[str, Any]:
    rag_orchestrator_url = os.getenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL")
    if not rag_orchestrator_url:
        raise EvaluatorClientError(
            message="URL de l'orchestrator non configurée",
            details={"env_var": "RAG_ORCHESTRATOR_ASK_QUESTION_URL"},
        )

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                rag_orchestrator_url,
                json={"question": question},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exception:
        raise EvaluatorClientError(
            message=f"Erreur HTTP {exception.response.status_code} lors de l'appel à l'orchestrator",
            details={"url": rag_orchestrator_url, "response": exception.response.text},
        ) from exception
    except httpx.ConnectError as exception:
        raise EvaluatorClientError(
            message="Impossible de se connecter à l'orchestrator",
            details={"url": rag_orchestrator_url, "error": str(exception)},
        ) from exception
    except httpx.TimeoutException as exception:
        raise EvaluatorClientError(
            message="Timeout lors de l'appel à l'orchestrator",
            details={"url": rag_orchestrator_url, "error": str(exception)},
        ) from exception
    except httpx.RequestError as exception:
        raise EvaluatorClientError(
            message="Erreur réseau lors de l'appel à l'orchestrator",
            details={"url": rag_orchestrator_url, "error": str(exception)},
        ) from exception
    except ValueError as exception:
        raise EvaluatorClientError(
            message="L'orchestrator a retourné une réponse JSON invalide",
            details={"url": rag_orchestrator_url},
        ) from exception

    if not isinstance(data, dict):
        raise EvaluatorClientError(
            message="L'orchestrator a retourné un format inattendu",
            details={"url": rag_orchestrator_url, "response": data},
        )

    return data
