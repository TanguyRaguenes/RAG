from typing import Any

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


def build_message(question: str, retrieve_chunks: list[dict[str, Any]],max_chars: int) -> list[dict[str, str]]:

    context= build_context(retrieve_chunks,max_chars)

    if context:
        system = (
            "Tu réponds UNIQUEMENT à partir du CONTEXTE. "
            "Si le CONTEXTE ne contient pas l'information, réponds exactement : \"Je ne sais pas.\" "
            "N'invente rien."
        )
        user_content = f"CONTEXTE:\n{context}\n\nQUESTION:\n{question}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
    
    # fallback : LLM pur
    return [
        {"role": "system", "content": "Tu es un assistant utile et concis."},
        {"role": "user", "content": question},
    ]