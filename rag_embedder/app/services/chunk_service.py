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

    chunks = []
    for doc in section_docs:
        if doc.page_content.strip():
            chunks.extend(splitter.split_text(doc.page_content))

    return chunks
