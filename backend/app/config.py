# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    omniroute_api_key: str = ""
    ollama_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    # Insecure fixed default for local/demo use only -- set JWT_SECRET in any
    # real deployment, or anyone can forge a valid login token.
    jwt_secret: str = "orca-dev-secret-change-me-before-any-real-deployment"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
