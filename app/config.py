import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel's /var/task deployment directory is read-only at runtime.
RUNTIME_DATA_DIR = (
    Path("/tmp/shopmate-ai") if os.getenv("VERCEL") else BASE_DIR
)

class Settings(BaseSettings):
    # Hosted providers sometimes expose an unset environment variable as an
    # empty string. Treat that the same as an absent value so typed defaults
    # below remain usable.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_ignore_empty=True
    )

    PROJECT_NAME: str = "ShopMate AI - Agentic Retail Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Environment & Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = RUNTIME_DATA_DIR / "data"
    CHROMA_PERSIST_DIR: Path = RUNTIME_DATA_DIR / "chroma_db"
    
    # Database (PostgreSQL with SQLite fallback)
    DATABASE_URL: str = os.getenv("DATABASE_URL") or f"sqlite:///{RUNTIME_DATA_DIR / 'shopmate.db'}"
    
    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "shopmate-super-secret-key-genai-2026-production-ready-32bytes")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Amazon & eBay Product API Settings
    AMAZON_PRODUCT_API_KEY: Optional[str] = os.getenv("AMAZON_PRODUCT_API_KEY", os.getenv("RAINFOREST_API_KEY", None))
    RAINFOREST_API_KEY: Optional[str] = os.getenv("RAINFOREST_API_KEY", None)
    EBAY_API_KEY: Optional[str] = os.getenv("EBAY_API_KEY", os.getenv("COUNTDOWN_API_KEY", None))
    COUNTDOWN_API_KEY: Optional[str] = os.getenv("COUNTDOWN_API_KEY", None)
    
    # LLM Settings (OpenAI / Gemini / Fallback)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Embedding Settings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "auto")
    EMBEDDING_DIMENSION: int = 384
    
    # RAG Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    HYBRID_SEARCH_ALPHA: float = 0.5  # 0.0 = BM25 only, 1.0 = Dense Vector only, 0.5 = Balanced
    TOP_K_RETRIEVAL: int = 6
    TOP_K_RERANKED: int = 3
    
    # Agent Guardrails
    CRITIC_MIN_GROUNDEDNESS_SCORE: float = 0.65
    ENABLE_SAFETY_GUARDRAILS: bool = True

settings = Settings()

# Ensure required directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "policies").mkdir(parents=True, exist_ok=True)
