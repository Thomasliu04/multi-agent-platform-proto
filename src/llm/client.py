"""LLM response types and the DeepSeek / HKGAI client."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field

from src.config import load_dotenv


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class OpenAICompatibleLLM:
    """Chat-completions client for DeepSeek and any HKGAI endpoint with the same shape."""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": schema} for schema in tools]
            payload["tool_choice"] = "auto"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
        message = data["choices"][0]["message"]
        calls: list[ToolCall] = []
        for raw in message.get("tool_calls") or []:
            arguments = raw.get("function", {}).get("arguments") or {}
            if isinstance(arguments, str):
                arguments = json.loads(arguments or "{}")
            calls.append(
                ToolCall(
                    id=raw.get("id") or f"call-{len(calls)}",
                    name=raw["function"]["name"],
                    arguments=arguments,
                )
            )
        return LLMResponse(content=message.get("content") or "", tool_calls=calls)


def build_llm(provider: str | None = None):
    from src.llm.mock import MockLLM

    load_dotenv()
    selected = (provider or os.getenv("LLM_PROVIDER") or "mock").strip().lower()
    if selected == "mock":
        return MockLLM()
    if selected == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            print("DEEPSEEK_API_KEY is empty. Falling back to the mock model.")
            return MockLLM()
        return OpenAICompatibleLLM(
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        )
    if selected == "hkgai":
        api_key = os.getenv("HKGAI_API_KEY", "")
        base_url = os.getenv("HKGAI_BASE_URL", "")
        model = os.getenv("HKGAI_MODEL", "")
        if not api_key or not base_url or not model:
            print("HKGAI settings are incomplete. Falling back to the mock model.")
            return MockLLM()
        return OpenAICompatibleLLM(base_url=base_url, api_key=api_key, model=model)
    raise ValueError(f"Unknown LLM_PROVIDER '{selected}'. Use mock, deepseek, or hkgai.")
