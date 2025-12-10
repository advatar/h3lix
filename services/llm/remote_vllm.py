from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from .base import LLMClient, LLMRequest, LLMResponse


@dataclass
class RemoteVLLMConfig:
    base_url: Optional[str] = None  # e.g., https://llm.internal/v1/generate
    model: Optional[str] = None
    api_token: Optional[str] = None
    timeout: float = 30.0


class RemoteVLLMClient(LLMClient):
    """
    Minimal HTTP client for a vLLM/Triton style text generation endpoint.
    Expects a POST JSON API with fields: model, prompt, max_tokens, temperature, stop.
    """

    def __init__(self, config: Optional[RemoteVLLMConfig] = None):
        self.config = config or RemoteVLLMConfig()
        self.base_url = self.config.base_url or os.getenv("REMOTE_LLM_URL")
        self.model = self.config.model or os.getenv("REMOTE_LLM_MODEL") or "llama"
        self.api_token = self.config.api_token or os.getenv("REMOTE_LLM_TOKEN")
        if not self.base_url:
            raise RuntimeError("Remote vLLM base_url is not configured (set REMOTE_LLM_URL).")

    def generate(self, req: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.model,
            "prompt": req.prompt if not req.system_prompt else f"{req.system_prompt.strip()}\n\n{req.prompt.strip()}",
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if req.stop:
            payload["stop"] = req.stop
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        request = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as resp:
                body = resp.read().decode("utf-8")
                parsed = json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
            raise RuntimeError(f"Remote LLM HTTP error: {exc.code} {detail}") from exc
        except Exception as exc:  # pragma: no cover - network errors
            raise RuntimeError(f"Remote LLM request failed: {exc}") from exc

        text = ""
        prompt_tokens = None
        completion_tokens = None
        if isinstance(parsed, dict):
            text = parsed.get("text") or parsed.get("completion") or parsed.get("data", parsed)
            meta = parsed.get("usage") or {}
            prompt_tokens = meta.get("prompt_tokens")
            completion_tokens = meta.get("completion_tokens")
        return LLMResponse(
            text=str(text),
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
