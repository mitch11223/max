"""
LLM client adapters.

Both use OpenAI-compatible /v1/chat/completions endpoints.
Both implement the same interface: async complete(prompt: str) -> str

Usage:
    from llm import XAIClient, OllamaClient

    grok   = XAIClient(api_key="xai-...", model="grok-4")
    router = OllamaClient(model="glm-4.7-flash")

    response = await grok.complete("What is the capital of France?")
"""

import httpx


_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class XAIClient:
    """
    Async client for xAI's OpenAI-compatible API (grok-4, etc.)
    Base URL: https://api.x.ai/v1
    """

    def __init__(
        self,
        api_key: str,
        model: str = "grok-4",
        base_url: str = "https://api.x.ai/v1",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def __repr__(self):
        return f"XAIClient(model={self.model})"


class OllamaClient:
    """
    Async client for Ollama's OpenAI-compatible API.
    Base URL: http://127.0.0.1:11434/v1
    Used for cheap/fast routing classification calls (glm-4.7-flash, etc.)
    """

    def __init__(
        self,
        model: str = "glm-4.7-flash",
        base_url: str = "http://127.0.0.1:11434/v1",
        max_tokens: int = 512,
        temperature: float = 0.2,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        headers = {
            "Authorization": "Bearer ollama",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def __repr__(self):
        return f"OllamaClient(model={self.model})"
