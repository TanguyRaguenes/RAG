import os
import posixpath
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from app.core.config import EmbedderConfig
from app.core.exceptions import MarkdownProcessingException
from app.dal.clients.embedding_client import embed as client_embed
from app.dal.clients.retriever_client import save_items as client_save_items
from app.domain.models.document_model import DocumentBase, DocumentsBase
from app.schemas.document_to_ingest_schema import (
    ChunkToIngest,
    DocumentsToIngest,
    DocumentToIngest,
)
from app.schemas.ingest_bulk_response_schema import IngestBulkResponseBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.schemas.vector_store_items_schema import (
    CollectionProfile,
    VectorMetadataBase,
    VectorStoreItemsBase,
)
from app.services.chunk_service import chunk_text
from app.services.load_documents_service import load_documents


async def ingest_documents(
    documents: DocumentsBase,
    config: EmbedderConfig,
    collection_profile: CollectionProfile = "default",
) -> SaveItemsResponseBase:
    """Charge, découpe, vectorise et sauvegarde les documents dans le retriever.

    Args:
        documents: Contenus textuels retournés par ChromaDB ou à ingérer.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        collection_profile: Collection logique ciblée dans le retriever.

    Returns:
        Réponse de sauvegarde retournée par le retriever après ingestion.

    Raises:
        MarkdownProcessingException: Si aucun document ou aucun chunk exploitable
            n'est disponible pour produire un snapshot sûr.
    """
    if not documents.documents:
        raise MarkdownProcessingException(
            internal_details={
                "operation": "ingest_documents",
                "reason": "no_document",
            },
        )

    documents_to_ingest = DocumentsToIngest(documents=[])

    # On itère sur tous les fichiers qui se trouves dans le dossier wikis
    for document in documents.documents:
        document_to_ingest: DocumentToIngest = await prepare_document_to_ingest(
            document, config
        )
        documents_to_ingest.documents.append(document_to_ingest)

    # On converti au format attendu par ChromaDB
    vector_store_items = convert_to_chroma_format(
        documents_to_ingest,
        collection_profile,
    )
    if not vector_store_items.ids:
        raise MarkdownProcessingException(
            internal_details={
                "operation": "ingest_documents",
                "reason": "no_chunk",
                "document_count": len(documents.documents),
            },
        )

    # On va contacter le container avec ChromaDB pour demander la sauvegarde des documents
    vector_store_items.delete_obsolete = True
    vector_store_items.replace_collection = collection_profile == "evaluation"
    save_items_response = await client_save_items(vector_store_items)

    return save_items_response


async def ingest_all_documents(
    config: EmbedderConfig,
    collection_profile: CollectionProfile = "default",
) -> IngestBulkResponseBase:
    """Orchestre une ingestion complète depuis les fichiers jusqu'au retriever.

    Args:
        config: Configuration de chunking et d'embedding du service.
        collection_profile: Profil déterminant le dossier source et la collection cible.

    Returns:
        Compteurs et horodatages conservant le contrat HTTP existant.
    """
    start = time.perf_counter()
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    source_directory = _get_source_directory(collection_profile)
    documents = await load_documents(source_directory)
    result = await ingest_documents(documents, config, collection_profile)
    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    return IngestBulkResponseBase(
        started_at=started_at,
        finished_at=datetime.now(UTC).isoformat(timespec="seconds"),
        duration=f"{minutes:02d}:{seconds:02d}",
        collection_count_before=result.collection_count_before,
        collection_count_after=result.collection_count_after,
    )


def convert_to_chroma_format(
    documents_to_ingest: DocumentsToIngest,
    collection_profile: CollectionProfile = "default",
) -> VectorStoreItemsBase:
    """Convertit des documents préparés en structure compatible avec ChromaDB.

    Args:
        documents_to_ingest: Documents découpés et enrichis prêts à être transformés au format ChromaDB.
        collection_profile: Collection logique jointe au lot vectoriel.

    Returns:
        Items vectoriels prêts à être envoyés au retriever.
    """
    all_ids: list[str] = []
    all_texts: list[str] = []
    all_embeddings: list[list[float]] = []
    all_metadatas: list[VectorMetadataBase] = []

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
        include_saved_items=False,
        collection_profile=collection_profile,
    )


def _get_source_directory(collection_profile: CollectionProfile) -> Path | None:
    """Résout le dossier fixe correspondant au profil d'ingestion.

    Args:
        collection_profile: Profil `default` ou `evaluation` validé par FastAPI.

    Returns:
        Dossier explicite des wikis gold, ou `None` pour le dossier standard.
    """
    if collection_profile == "evaluation":
        return Path(os.getenv("RAG_EVALUATION_WIKIS_DIR", "/data/evaluation-wikis"))
    return None


def clean_title(title: str) -> str:
    """Nettoie un titre documentaire pour produire un identifiant stable.

    Args:
        title: Titre ou nom de fichier documentaire à nettoyer.

    Returns:
        Titre décodé et normalisé sans extension Markdown.
    """
    decoded_title = unquote(title)

    clean_title = decoded_title.replace(".md", "").replace("-", " ").replace("_", " ")

    return " ".join(clean_title.split())


async def prepare_document_to_ingest(
    document: DocumentBase, config: EmbedderConfig
) -> DocumentToIngest:
    """Prépare les chunks et métadonnées d'un document avant ingestion vectorielle.

    Args:
        document: Document source contenant le chemin et le contenu Markdown à ingérer.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Document enrichi avec chunks, embeddings et métadonnées d'ingestion.
    """
    document_to_ingest: DocumentToIngest = DocumentToIngest(chunks=[])

    # on découpe le fichier en chunks
    chunks: list[str] = chunk_text(document.content, config)
    document_context: str = clean_title(document.path.split("/")[-1])
    texts_to_embed: list[str] = []
    chunks_metadata: list[VectorMetadataBase] = []

    for i, chunk in enumerate(chunks):
        # 1. EXTRACTION DES LIENS
        # La regex capture ce qui est entre parenthèses (...) juste après des crochets [...]
        raw_links = re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", chunk)
        clean_links = [
            normalized_link
            for link in raw_links
            if (normalized_link := normalize_markdown_link(link, document.path))
            is not None
        ]

        # On transforme la liste en string pour le stockage simple dans ChromaDB
        links_metadata = ",".join(clean_links)

        # on prépare le contexte global du document (à partir du nom de fichier)
        # -> découplage (Decoupling) entre la sémantique (le sens) et le contenu (le texte)
        # text_to_embed = f"Contexte du document : {document_context}\nContenu : {chunk}"
        text_to_embed = f"TITLE={document_context} | PATH={document.path}\n{chunk}"
        texts_to_embed.append(text_to_embed)
        chunks_metadata.append(
            VectorMetadataBase(
                path=document.path,
                title=document_context,
                chunk_index=i,
                related_links=links_metadata,
                has_links=bool(clean_links),
            )
        )

    if not texts_to_embed:
        return document_to_ingest

    # on convertit les chunks en float en un seul appel batch
    embeddings: list[list[float]] = await client_embed(texts_to_embed, config, False)

    for i, chunk in enumerate(chunks):
        # On génère le formalisme attendu par ChromaDB
        chunk_to_ingest: ChunkToIngest = ChunkToIngest(
            id=f"{document_context}#chunk_{i}#{document.path}",
            chunk=chunk,
            embeded_text=embeddings[i],
            metadatas=chunks_metadata[i],
        )

        document_to_ingest.chunks.append(chunk_to_ingest)

    return document_to_ingest


def normalize_markdown_link(link: str, source_path: str) -> str | None:
    """Normalise un lien Markdown interne vers un chemin wiki relatif.

    Args:
        link: Cible brute extraite des parenthèses Markdown.
        source_path: Chemin relatif du document contenant le lien.

    Returns:
        Chemin Markdown relatif normalisé, ou `None` pour un lien externe,
        une ancre ou une ressource non Markdown.
    """
    target = link.strip().split(maxsplit=1)[0]
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None

    decoded_path = unquote(parsed.path).replace("\\", "/")
    if decoded_path.startswith("/"):
        candidate = decoded_path.lstrip("/")
    else:
        source_directory = posixpath.dirname(source_path)
        candidate = posixpath.join(source_directory, decoded_path)

    normalized = posixpath.normpath(candidate)
    if normalized in {"", "."} or normalized.startswith("../"):
        return None

    extension = posixpath.splitext(normalized)[1].lower()
    if extension and extension != ".md":
        return None
    if not extension:
        normalized = f"{normalized}.md"
    return normalized
