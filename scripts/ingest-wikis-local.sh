#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")
WIKIS_DIR=${RAG_WIKIS_PATH:-$(dirname -- "$PROJECT_DIR")/wikis}

log() {
    printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

if [ ! -d "$WIKIS_DIR" ]; then
    log "RAG wiki ingestion failed: ingestion not triggered because wiki directory does not exist: $WIKIS_DIR"
    exit 1
fi

if [ -z "$(find "$WIKIS_DIR" -type f -name '*.md' ! -path '*/.git/*' -print -quit)" ]; then
    log "RAG wiki ingestion skipped: wiki directory is empty or contains no Markdown files: $WIKIS_DIR"
    exit 0
fi

log "RAG wiki ingestion started"
RESPONSE_FILE=$(mktemp)
trap 'rm -f "$RESPONSE_FILE"' EXIT

if ! HTTP_STATUS=$(curl -sS -o "$RESPONSE_FILE" -w '%{http_code}' -X POST http://localhost:8002/ingest/bulk); then
    printf '\n'
    log "RAG wiki ingestion failed: rag_embedder is unreachable"
    exit 1
fi

cat "$RESPONSE_FILE"
printf '\n'

case "$HTTP_STATUS" in
    2??) ;;
    *)
        log "RAG wiki ingestion failed: bulk ingestion request returned HTTP $HTTP_STATUS"
        exit 1
        ;;
esac

find "$WIKIS_DIR" -mindepth 1 -delete
log "RAG wiki source directory cleared after successful ingestion: $WIKIS_DIR"
log "RAG wiki ingestion finished"
