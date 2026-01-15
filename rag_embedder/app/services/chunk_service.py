import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Découpe le texte en segments (chunks) intelligents en préservant la structure sémantique.

# Cette méthode utilise une stratégie "Récursive" pour éviter de couper le texte brutalement :
# 1. Elle essaie d'abord de couper aux paragraphes (\n\n) pour garder les idées groupées.
# 2. Si le morceau est trop gros, elle coupe aux retours à la ligne (\n).
# 3. Si nécessaire, elle coupe aux espaces.

# Objectifs :
# - Sémantique : Fournir des phrases complètes et cohérentes pour ne pas perdre le sens. Avec un chevauchement (overlap) pour ne pas perdre d'informations aux frontières de coupure.
# - Technique : Respecter la limite stricte de tokens (fenêtre de contexte) imposée par le modèle d'embedding, qui ne peut pas traiter de trop longs textes d'un seul coup.


def chunk_text(text: str, config: dict) -> list[str]:
    size_chars = config["chunking"]["size_chars"]
    overlap_chars = config["chunking"]["overlap_chars"]

    text = text.replace("[[_TOC_]]", "").strip()
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=size_chars,
        chunk_overlap=overlap_chars,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = text_splitter.split_text(text)

    return chunks
