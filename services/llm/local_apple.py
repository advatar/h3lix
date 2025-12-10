from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from .base import LLMClient, LLMRequest, LLMResponse


@dataclass
class LocalAppleConfig:
    model_path: Optional[str] = None  # HF repo id or local path
    dtype: str = "float16"
    default_max_tokens: int = 256
    default_temperature: float = 0.7


class AppleLocalLLM(LLMClient):
    """
    Minimal local LLM client for Apple Silicon using MLX/MLX-LM.
    Requires `pip install mlx-lm` and a downloaded Apple/MLX model.
    """

    def __init__(self, config: Optional[LocalAppleConfig] = None):
        self.config = config or LocalAppleConfig()
        self.model_path = self.config.model_path or os.getenv("APPLE_LLM_MODEL")
        self._model: Any = None
        self._tokenizer: Any = None
        self._generate_fn = None

    def _compose_prompt(self, req: LLMRequest) -> str:
        if req.system_prompt:
            return f"{req.system_prompt.strip()}\n\n{req.prompt.strip()}"
        return req.prompt

    def _ensure_model(self) -> None:
        if self._model is not None and self._tokenizer is not None and self._generate_fn is not None:
            return
        if not self.model_path:
            raise RuntimeError(
                "Local Apple LLM not configured. Set APPLE_LLM_MODEL to a local Apple/MLX model path or pass model_path."
            )
        try:
            from mlx_lm import load, generate
        except ImportError as exc:
            raise RuntimeError("mlx_lm is required for the local Apple model. Install with `pip install mlx-lm`.") from exc
        self._model, self._tokenizer = load(self.model_path, dtype=self.config.dtype)
        self._generate_fn = generate

    def generate(self, req: LLMRequest) -> LLMResponse:
        self._ensure_model()
        prompt = self._compose_prompt(req)
        max_tokens = req.max_tokens or self.config.default_max_tokens
        temperature = req.temperature if req.temperature is not None else self.config.default_temperature
        kwargs = {"max_tokens": max_tokens, "temp": temperature}
        if req.stop:
            kwargs["stop"] = req.stop
        try:
            text = self._generate_fn(self._model, self._tokenizer, prompt, **kwargs)
        except TypeError:
            kwargs.pop("stop", None)
            text = self._generate_fn(self._model, self._tokenizer, prompt, **kwargs)
        return LLMResponse(
            text=str(text),
            model=self.model_path or "local-apple-mlx",
            prompt_tokens=None,
            completion_tokens=None,
        )
