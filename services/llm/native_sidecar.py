from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from .base import LLMClient, LLMRequest, LLMResponse


@dataclass
class NativeSidecarConfig:
    base_url: Optional[str] = None  # e.g., http://localhost:8081/generate
    model: Optional[str] = None     # name understood by the Swift sidecar
    api_token: Optional[str] = None
    timeout: float = 30.0


class NativeSidecarClient(LLMClient):
    """
    Client for a local Swift FoundationModels sidecar exposed over HTTP.

    Expected JSON POST payload: {model, prompt, maxTokens, temperature, stop?}
    Expected JSON response: {text, usage: {prompt_tokens?, completion_tokens?}}
    """

    def __init__(self, config: Optional[NativeSidecarConfig] = None):
        self.config = config or NativeSidecarConfig()
        self.base_url = self.config.base_url or os.getenv("NATIVE_LLM_URL") or "http://localhost:8081/generate"
        self.model = self.config.model or os.getenv("NATIVE_LLM_MODEL") or "native"
        self.api_token = self.config.api_token or os.getenv("NATIVE_LLM_TOKEN")

    def generate(self, req: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.model,
            "prompt": req.prompt if not req.system_prompt else f"{req.system_prompt.strip()}\n\n{req.prompt.strip()}",
            "maxTokens": req.max_tokens,
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
            raise RuntimeError(f"Native sidecar HTTP error: {exc.code} {detail}") from exc
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Native sidecar request failed: {exc}") from exc

        text = ""
        prompt_tokens = None
        completion_tokens = None
        if isinstance(parsed, dict):
            text = parsed.get("text") or parsed.get("completion") or parsed
            meta = parsed.get("usage") or {}
            prompt_tokens = meta.get("prompt_tokens")
            completion_tokens = meta.get("completion_tokens")
        return LLMResponse(
            text=str(text),
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
