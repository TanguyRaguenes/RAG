from typing import Any

# SCÉNARIO : Le Retriever a trouvé 5 chunks de 1000 caractères chacun.
# Total théorique : 5000 caractères.
# Problème : la limite (max_chars) est fixée à 4500 pour ne pas surcharger le CPU.
# → Cette fonction va laisser entrer les chunks tant qu'il y a de la place, et refuse les suivants (donc dans ce cas de figure seulement le 4 premiers).


def build_context(chunks: list[dict[str, Any]], config: dict) -> str:
    max_chars = config["context_builder"]["max_chars"]

    parts: list[str] = []
    total = 0

    for chunk in chunks:
        meta = chunk.get("metadata") or {}

        block = (
            f"SOURCE: {meta.get('title')}\n"
            f"PATH: {meta.get('path')}\n"
            f"CHUNK: {meta.get('chunk_index')}\n"
            f"CONTENU:\n{chunk.get('document', '')}"
        ).strip()

        if total + len(block) > max_chars:
            break

        parts.append(block)
        total += len(block) + 2

    return "\n\n".join(parts)


def build_prompt(
    question: str, retrieve_chunks: list[dict[str, Any]], config: dict
) -> list[dict[str, str]]:
    context = build_context(retrieve_chunks, config)

    if context:
        system = (
            "Tu réponds UNIQUEMENT à partir du CONTEXTE. "
            'Si le CONTEXTE ne contient pas l\'information, réponds exactement : "Je ne sais pas." '
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
