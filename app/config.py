import os


class Settings:
    embedding_base_url: str = os.getenv("RAG_EMBEDDING_BASE_URL", "http://localhost:1234/v1")
    embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text-v1.5")
    llm_model: str = os.getenv("RAG_LLM_MODEL", "claude-sonnet-4-20250514")
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
    top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    host: str = os.getenv("RAG_HOST", "0.0.0.0")
    port: int = int(os.getenv("RAG_PORT", "8000"))
