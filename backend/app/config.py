from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/mindbridge"

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str  # No default — must be set in .env / environment
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── AI (Gemini) ───────────────────────────────────────────────────────────
    GEMINI_API_KEY: str  # No default — must be set in .env / environment

    # ── Redis (conversation memory) ───────────────────────────────────────────
    # docker-compose adds Redis on port 6379 by default.
    # Override in .env if your Redis lives elsewhere.
    REDIS_URL: str = "redis://localhost:6380"
    MEMORY_TTL_SECONDS: int = 86_400          # 24 h — auto-expire idle sessions

    # ── App ───────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000"
    CORPUS_PATH: str = "./corpus/mental_health_corpus.json"
    APP_ENV: str = "development"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
