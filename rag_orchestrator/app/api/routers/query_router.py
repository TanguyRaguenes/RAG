from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_current_user,
    get_question_orchestration_service,
)
from app.schemas.ask_question_request_schema import AskQuestionRequestBase
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.schemas.retrieve_chunks_request_schema import RetrieveChunksRequestBase
from app.schemas.retrieve_chunks_response_schema import RetrieveChunksResponseBase
from app.services.question_orchestration_service import (
    QuestionOrchestrationServiceProtocol,
)

router = APIRouter()
current_user_dependency = Depends(get_current_user)
orchestration_service_dependency = Depends(get_question_orchestration_service)


@router.post("/ask_question", response_model=AskQuestionResponseBase)
async def ask_question_route(
    body: AskQuestionRequestBase,
    current_user: AuthenticatedUser = current_user_dependency,
    orchestration_service: QuestionOrchestrationServiceProtocol = (
        orchestration_service_dependency
    ),
) -> AskQuestionResponseBase:
    """Adapte la requête HTTP de question vers le service d'orchestration.

    Args:
        body: Question et choix de fournisseur validés par Pydantic.
        current_user: Utilisateur authentifié injecté par FastAPI.
        orchestration_service: Service métier injecté pour exécuter le pipeline RAG.

    Returns:
        Réponse RAG conforme au contrat public existant.

    Raises:
        ApplicationError: Si le service refuse ou ne peut pas traiter la question.
    """
    return await orchestration_service.ask_question(body, current_user)


@router.post("/retrieve_chunks", response_model=RetrieveChunksResponseBase)
async def retrieve_chunks_route(
    body: RetrieveChunksRequestBase,
    current_user: AuthenticatedUser = current_user_dependency,
    orchestration_service: QuestionOrchestrationServiceProtocol = (
        orchestration_service_dependency
    ),
) -> RetrieveChunksResponseBase:
    """Adapte la requête HTTP de retrieval vers le service d'orchestration.

    Args:
        body: Question documentaire validée par Pydantic.
        current_user: Utilisateur authentifié injecté par FastAPI.
        orchestration_service: Service métier injecté pour exécuter le retrieval MCP.

    Returns:
        Chunks récupérés conformément au contrat public existant.

    Raises:
        ApplicationError: Si le service refuse ou ne peut pas traiter le retrieval.
    """
    return await orchestration_service.retrieve_chunks(body, current_user)
