import re
from urllib.parse import unquote

from app.dal.clients.embedding_client import embed_text as client_embed_text
from app.dal.clients.retriever_client import save_items as client_save_items
from app.domain.models.document_model import DocumentBase, DocumentsBase
from app.domain.models.vector_store_item_model import VectorStoreItemsBase
from app.schemas.document_to_ingest_schema import (
    ChunkToIngest,
    DocumentsToIngest,
    DocumentToIngest,
)
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.services.chunk_service import chunk_text


async def ingest_documents(documents: DocumentsBase, config: dict) -> dict:
    documents_to_ingest: DocumentToIngest = DocumentsToIngest(documents=[])

    # On itère sur tous les fichiers qui se trouves dans le dossier wikis
    for document in documents.documents:
        document_to_ingest: DocumentToIngest = await prepare_document_to_ingest(
            document, config
        )
        documents_to_ingest.documents.append(document_to_ingest)

    # On converti au format attendu par ChromaDB
    vector_store_items: VectorStoreItemsBase = convert_to_chroma_format(
        documents_to_ingest
    )

    # On va contacter le container avec ChromaDB pour demander la sauvegarde des documents
    save_items_response: SaveItemsResponseBase = await client_save_items(
        vector_store_items
    )

    return save_items_response


def convert_to_chroma_format(
    documents_to_ingest: DocumentsToIngest,
) -> VectorStoreItemsBase:
    all_ids = []
    all_texts = []
    all_embeddings = []
    all_metadatas = []

    # 1. On parcourt chaque document
    for doc in documents_to_ingest.documents:
        # 2. On parcourt chaque chunk
        for chunk_obj in doc.chunks:
            all_ids.append(chunk_obj.id)
            all_texts.append(chunk_obj.chunk)
            all_embeddings.append(chunk_obj.embeded_text)
            all_metadatas.append(chunk_obj.metadatas)

    return VectorStoreItemsBase(
        ids=all_ids,
        documents=all_texts,
        embeddings=all_embeddings,
        metadatas=all_metadatas,
    )


def clean_title(title: str) -> str:
    decoded_title = unquote(title)

    clean_title = decoded_title.replace(".md", "").replace("-", " ").replace("_", " ")

    return " ".join(clean_title.split())


async def prepare_document_to_ingest(
    document: DocumentBase, config: dict
) -> DocumentToIngest:
    document_to_ingest: DocumentToIngest = DocumentToIngest(chunks=[])

    # on découpe le fichier en chunks
    chunks: list[str] = chunk_text(document.content, config)
    document_context: str = clean_title(document.path.split("/")[-1])

    for i, chunk in enumerate(chunks):
        # 1. EXTRACTION DES LIENS
        # La regex capture ce qui est entre parenthèses (...) juste après des crochets [...]
        raw_links = re.findall(r"\[.*?\]\((.*?)\)", chunk)

        clean_links = []
        for link in raw_links:
            # A. On décode les caractères URL (ex: "%2D" devient "-")
            # decoded_link = unquote(link)

            # B. On retire les espaces autour au cas où
            clean_link = link.strip()
            clean_links.append(f"{clean_link[1:]}.md")

        # On transforme la liste en string pour le stockage simple dans ChromaDB
        links_metadata = ",".join(clean_links)

        # on prépare le contexte global du document (à partir du nom de fichier)
        # -> découplage (Decoupling) entre la sémantique (le sens) et le contenu (le texte)
        # text_to_embed = f"Contexte du document : {document_context}\nContenu : {chunk}"
        text_to_embed = f"TITLE={document_context} | PATH={document.path}\n{chunk}"

        # on convertit les chunks en float
        embed_text: list[float] = await client_embed_text(text_to_embed, config, False)

        # On génère le formalisme attendu par ChromaDB
        chunk_to_ingest: ChunkToIngest = ChunkToIngest(
            id=f"{document_context}#chunk_{i}#{document.path}",
            chunk=chunk,
            embeded_text=embed_text,
            metadatas={
                "path": document.path,
                "title": document_context,
                "chunk_index": i,
                "related_links": links_metadata,
                "has_links": len(raw_links) > 0,
            },
        )

        document_to_ingest.chunks.append(chunk_to_ingest)

    return document_to_ingest
