import re
from typing import Any

# SCÉNARIO : Le Retriever a trouvé 5 chunks de 1000 caractères chacun.
# Total théorique : 5000 caractères.
# Problème : la limite (max_chars) est fixée à 4500 pour ne pas surcharger le CPU.
# → Cette fonction va laisser entrer les chunks tant qu'il y a de la place, et refuse les suivants (donc dans ce cas de figure seulement le 4 premiers).


def build_context(chunks: list[dict[str, Any]], max_prompt_chars: int) -> str:

    parts: list[str] = []
    total = 0

    for index, chunk in enumerate(chunks, start=1):
        block = format_chunk_as_markdown(index, chunk)

        if total + len(block) > max_prompt_chars:
            break

        parts.append(block)
        total += len(block) + 2

    return "\n\n".join(parts)


CHUNK_DOCUMENT_PATTERN = re.compile(
    r"^\s*CONTEXT\s*:\s*(?P<context>.*?)\r?\nCONTENT\s*:\s*(?P<content>.*)\s*$",
    re.DOTALL,
)


def format_chunk_as_markdown(index: int, chunk: dict[str, Any]) -> str:
    meta = chunk.get("metadata") or {}
    title = meta.get("title") or "Non renseigné"
    path = meta.get("path") or "Non renseigné"
    chunk_index = meta.get("chunk_index")
    chunk_index_value = chunk_index if chunk_index is not None else "Non renseigné"
    section, content = parse_chunk_document(chunk.get("document") or "")

    section_block = (
        f"### Section documentaire\n\n{section}\n\n" if section else ""
    )

    return (
        f"## Chunk {index} - {title}\n\n"
        "### Métadonnées\n\n"
        f"- **Source** : {title}\n"
        f"- **Chemin** : `{path}`\n"
        f"- **Index du chunk** : {chunk_index_value}\n\n"
        f"{section_block}"
        f"### Extrait documentaire\n\n"
        f"{content}"
    ).strip()


def parse_chunk_document(document: str) -> tuple[str | None, str]:
    match = CHUNK_DOCUMENT_PATTERN.match(document)

    if not match:
        return None, document.strip()

    section = match.group("context").strip()
    content = match.group("content").strip()

    return section, content


def build_prompt(
    question: str,
    retrieve_chunks: list[dict[str, Any]],
    max_prompt_chars: int,
) -> list[dict[str, str]]:
    context = build_context(retrieve_chunks, max_prompt_chars)

    system = """
    # Rôle

    Tu es un assistant qui répond aux questions des développeurs.

    # Règles

    - Réponds uniquement à partir du contexte documentaire fourni.
    - Si le contexte documentaire ne contient pas l'information, réponds exactement :
    **« La réponse ne se trouve pas dans le contexte fourni par le RAG. »**
    - N'invente aucune information.
    """.strip()
    
    user_content = (
        f"# Question\n\n{question}\n\n"
        f"# Contexte documentaire\n\n{context}\n\n"
        "# Attendu\n\n"
        "Fournis une réponse directement exploitable par un développeur."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    
