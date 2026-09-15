# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    omniroute_api_key: str = ""
    ollama_api_key: str = ""
    imd_api_key: str = ""
    mosdac_token: str = ""
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    model_config = SettingsConfigDict(env_file=".env")



@lru_cache
def get_settings() -> Settings:
    return Settings()
