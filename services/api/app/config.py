from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM providers
    gemini_api_key: str = ""
    groq_api_key: str = ""
    llm_primary: str = "gemini"
    llm_fallback: str = "groq"

    # Stores
    database_url: str = "postgresql://manak:manak@localhost:5432/manak_setu"
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "manak_setu"

    # Behaviour
    confidence_threshold: float = 0.65
    crawl_delay_seconds: float = 1.5
    log_level: str = "INFO"

    # Retrieval
    qdrant_collection: str = "standards"
    embedding_model: str = "BAAI/bge-m3"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    index_meta_path: str = "data/index_meta.json"
    rerank_top_k: int = 40


@lru_cache
def get_settings() -> Settings:
    return Settings()
