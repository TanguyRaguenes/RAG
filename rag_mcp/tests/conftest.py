import sys
import os
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("RAG_ORCHESTRATOR_RETRIEVE_CHUNKS_URL", "http://rag/retrieve_chunks")
os.environ.setdefault("RAG_MCP_OIDC_ISSUER", "https://auth.example.test")
os.environ.setdefault("RAG_MCP_OIDC_JWKS_URI", "https://auth.example.test/jwks.json")
os.environ.setdefault("RAG_MCP_OIDC_ALLOWED_AUDIENCES", "https://mcp.example.test/")
os.environ.setdefault("RAG_MCP_REQUIRED_SCOPES", "rag:mcp")
os.environ.setdefault("RAG_MCP_RESOURCE_SERVER_URL", "https://mcp.example.test")
