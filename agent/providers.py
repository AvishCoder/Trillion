import httpx
import json

PROVIDER_CONFIGS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
    },
}


class AIProvider:
    def __init__(self, provider_name: str, api_key: str):
        self.name = provider_name
        self.api_key = api_key
        config = PROVIDER_CONFIGS.get(provider_name)
        if not config:
            raise ValueError(f"Unknown provider: {provider_name}")
        self.base_url = config["base_url"]
        self.client = httpx.AsyncClient(timeout=180)

    async def chat_completion(self, model: str, messages: list, tools: list = None, max_tokens: int = 4096):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.name == "openrouter":
            headers["HTTP-Referer"] = "https://trillion-agent.onrender.com"
            headers["X-Title"] = "Trillion Agent"

        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        if response.status_code != 200:
            error_detail = response.text
            raise Exception(f"API error ({response.status_code}): {error_detail}")

        data = response.json()
        return data["choices"][0]["message"], data.get("usage", {})

    async def close(self):
        await self.client.aclose()
