# backend/app/llm.py
from google import genai
from app.config import get_settings

DEFAULT_MODEL = "gemini-3.5-flash"


def get_llm_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)
