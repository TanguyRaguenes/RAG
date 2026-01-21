import re

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# Découpe le texte en segments (chunks) intelligents en préservant la structure sémantique.


def chunk_text(text: str, config: dict) -> list[str]:
    size_chars = config["chunking"]["size_chars"]
    overlap_chars = config["chunking"]["overlap_chars"]

    text = text.replace("[[_TOC_]]", "").strip()
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    # 1° Découpage du document par section
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ]
    )
    section_docs = header_splitter.split_text(text)

    # 2° Découpage récursif classique à l’intérieur des sections
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size_chars,
        chunk_overlap=overlap_chars,
        length_function=len,
        is_separator_regex=False,
    )

    chunks: list[str] = []
    # for doc in section_docs:
    #     if doc.page_content.strip():
    #         chunks.extend(splitter.split_text(doc.page_content))

    for doc in section_docs:
        # On construit le "fil d'Ariane" (ex: Réalisation > Etape 1)
        # On récupère les métadonnées créées par le MarkdownHeaderTextSplitter
        breadcrumbs = [
            doc.metadata.get("h1"),
            doc.metadata.get("h2"),
            doc.metadata.get("h3"),
        ]
        # On filtre les valeurs vides et on les joint avec " > "
        context_string = " > ".join([b for b in breadcrumbs if b])

        # On "colle" le contexte au début du contenu
        if context_string:
            content_with_context = (
                f"CONTEXT : {context_string}\nCONTENT : {doc.page_content}"
            )
        else:
            content_with_context = doc.page_content

        # On découpe ce texte enrichi et on l'ajoute à la liste
        if content_with_context.strip():
            chunks.extend(splitter.split_text(content_with_context))

    return chunks
