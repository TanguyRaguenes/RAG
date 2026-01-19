from typing import Any
from app.domain.models.judge_response_model import JudgeOutput
from app.domain.models.judge_response_model import judge_parser

def build_context(chunks: list[dict[str, Any]], max_chars: int) -> str:
    parts: list[str] = []
    total = 0

    for c in chunks:
        meta = c.get("metadata") or {}
        header = f"[{meta.get('path')} | chunk {meta.get('chunk')}]"
        block = f"{header}\n{c.get('document', '')}".strip()

        if total + len(block) > max_chars:
            break

        parts.append(block)
        total += len(block) + 2

    return "\n\n".join(parts)


def build_judge_messages(
    question: str,
    generated_answer: str,
    reference_answer: str,
    retrieved_chunks: list[dict[str, Any]],
    max_context_chars: int = 12000,
) -> list[dict[str, str]]:
    context = build_context(retrieved_chunks, max_context_chars)

    format_instructions = judge_parser.get_format_instructions()

    system = (
        "You are an expert evaluator assessing the quality of answers. "
        "Evaluate the generated answer by comparing it to the reference answer. "
        "Only give 5/5 scores for perfect answers.\n\n"
        f"{format_instructions}"
    )

    user = f"""Question:
        {question}

        Generated Answer:
        {generated_answer}

        Reference Answer:
        {reference_answer}

        Retrieved Context:
        {context}

        Rules:
        - If the answer is wrong, accuracy MUST be 1.
        - Be strict. Only give 5 for perfect answers.
        """

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]