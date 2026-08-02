from typing import Any

from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from app.core.config import EvaluatorConfig
from app.core.exceptions import JudgeEvaluationException
from app.dal.clients.judge_client import ConfiguredJudgeClient, JudgeClient
from app.domain.models.judge_response_model import judge_parser
from app.schemas.answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.judge_schema import JudgeMessage
from app.services.prompt_builder_service import build_judge_messages


async def evaluate_answer(
    config: EvaluatorConfig,
    question: str,
    generated_answer: str,
    reference_answer: str,
    retrieved_chunks: list[dict[str, Any]],
    expected_answer_points: list[str] | None = None,
    expected_behavior: str = "answer",
    judge_client: JudgeClient | None = None,
) -> AnswerEvaluationBase:
    """Demande au juge LLM d'évaluer la réponse générée par le RAG.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
        generated_answer: Réponse produite par le RAG à évaluer.
        reference_answer: Réponse attendue du dataset d'évaluation.
        retrieved_chunks: Chunks retournés par le retriever ou l'orchestrator.
        expected_answer_points: Points factuels attendus dans une bonne réponse.
        expected_behavior: Comportement attendu par le dataset, `answer` ou `refuse`.
        judge_client: Client externe injecté, ou client sélectionné par la configuration.

    Returns:
        Scores JSON produits par le juge LLM pour la réponse RAG.

    Raises:
        EvaluatorClientError: Si l'appel au fournisseur du juge échoue.
        JudgeEvaluationException: Si le jugement ne respecte pas le schéma métier.
    """
    messages = [
        JudgeMessage.model_validate(message)
        for message in build_judge_messages(
            question=question,
            generated_answer=generated_answer,
            reference_answer=reference_answer,
            retrieved_chunks=retrieved_chunks,
            expected_answer_points=expected_answer_points,
            expected_behavior=expected_behavior,
            max_context_chars=(
                config.llm.api.max_prompt_chars
                if config.judge_provider == "api"
                else config.llm.local.max_prompt_chars
            ),
        )
    ]
    client = judge_client or ConfiguredJudgeClient.from_config(config)
    raw_judgement = await client.judge(messages)

    try:
        judge_output = judge_parser.parse(raw_judgement)
        return AnswerEvaluationBase.model_validate(judge_output.model_dump())
    except (OutputParserException, ValidationError) as exception:
        raise JudgeEvaluationException(
            message="Le jugement LLM ne respecte pas le format attendu",
            internal_message="Parsing de la réponse métier du juge impossible",
            internal_details={"error_type": type(exception).__name__},
        ) from exception
