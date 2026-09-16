# backend/app/config.py
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    omniroute_api_key: str = ""
    ollama_api_key: str = ""
    ollama_api_key_2: str = ""
    ollama_api_key_3: str = ""
    ollama_api_key_4: str = ""
    ollama_api_key_5: str = ""
    ollama_api_key_6: str = ""
    ollama_api_key_7: str = ""
    imd_api_key: str = ""
    mosdac_token: str = ""
    stormglass_api_key: str = ""

    @property
    def ollama_keys(self) -> list[str]:
        keys = [
            self.ollama_api_key,
            self.ollama_api_key_2,
            self.ollama_api_key_3,
            self.ollama_api_key_4,
            self.ollama_api_key_5,
            self.ollama_api_key_6,
            self.ollama_api_key_7,
        ]
        return [k.strip() for k in keys if k and k.strip()]
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    # Insecure fixed default for local/demo use only -- set JWT_SECRET in any
    # real deployment, or anyone can forge a valid login token.
    jwt_secret: str = "orca-dev-secret-change-me-before-any-real-deployment"

    # `extra="ignore"`: backend/.env accumulates keys for connectors that
    # aren't wired into a Settings field yet (see .env.example) -- an unused
    # key sitting in .env shouldn't break Settings() for everyone else.
    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), ".env"),
        extra="ignore",
    )



@lru_cache
def get_settings() -> Settings:
    return Settings()
