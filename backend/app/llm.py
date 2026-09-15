# backend/app/llm.py
"""LLM client abstraction with a two-provider fallback chain.

Priority: Omniroute (local proxy, reliable JSON-schema enforcement).
Fallback: Ollama Cloud (manual JSON extraction, schema not enforced server-side).
"""
import json
import re

import httpx

from app.config import get_settings

OMNIROUTE_BASE_URL = "http://127.0.0.1:20128/v1"
OMNIROUTE_MODEL = "auto/best-fast"
OLLAMA_BASE_URL = "https://ollama.com/api"
OLLAMA_MODEL = "gemma4:31b"

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMClient:
    def __init__(self, omniroute_api_key: str, ollama_api_key: str):
        self._omniroute_api_key = omniroute_api_key
        self._ollama_api_key = ollama_api_key

    async def generate_text(self, system_prompt: str, user_message: str) -> str:
        try:
            return await self._omniroute_text(system_prompt, user_message)
        except Exception:
            return await self._ollama_text(system_prompt, user_message)

    async def generate_structured(
        self, system_prompt: str, user_message: str, schema: dict
    ) -> dict:
        try:
            return await self._omniroute_structured(system_prompt, user_message, schema)
        except Exception:
            return await self._ollama_structured(system_prompt, user_message, schema)

    async def _omniroute_text(self, system_prompt: str, user_message: str) -> str:
        payload = {
            "model": OMNIROUTE_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        data = await self._post_omniroute(payload)
        return data["choices"][0]["message"]["content"]

    async def _omniroute_structured(
        self, system_prompt: str, user_message: str, schema: dict
    ) -> dict:
        payload = {
            "model": OMNIROUTE_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "response", "strict": True, "schema": schema},
            },
        }
        data = await self._post_omniroute(payload)
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    async def _post_omniroute(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{OMNIROUTE_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self._omniroute_api_key}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def _ollama_text(self, system_prompt: str, user_message: str) -> str:
        data = await self._post_ollama(system_prompt, user_message)
        return data["message"]["content"]

    async def _ollama_structured(
        self, system_prompt: str, user_message: str, schema: dict
    ) -> dict:
        strict_prompt = (
            f"{system_prompt}\n\nRespond with ONLY a single JSON object matching this "
            f"shape, no markdown, no prose, no code fences: {json.dumps(schema)}"
        )
        for _ in range(2):
            data = await self._post_ollama(strict_prompt, user_message)
            content = data["message"]["content"]
            match = _JSON_OBJECT_RE.search(content)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            strict_prompt = (
                f"{strict_prompt}\n\nYour previous reply was not valid JSON. "
                "Reply with ONLY the JSON object, nothing else."
            )
        raise ValueError("Ollama fallback did not return valid JSON after retry")

    async def _post_ollama(self, system_prompt: str, user_message: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/chat",
                headers={"Authorization": f"Bearer {self._ollama_api_key}"},
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()


def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(
        omniroute_api_key=settings.omniroute_api_key,
        ollama_api_key=settings.ollama_api_key,
    )
