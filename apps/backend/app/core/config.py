from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "DecisionVault"
    app_env: str = "development"
    jwt_secret: str
    access_token_minutes: int = 60
    database_url: str
    cors_origins: str = "http://localhost:3000"
    storage_path: str = "/data/storage"
    ollama_url: str = "http://host.docker.internal:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_enabled: bool = True
    demo_tenant_slug: str = "acme"
    demo_email: str = "demo@decisionvault.ai"
    demo_password: str = "DecisionVault!"

    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
