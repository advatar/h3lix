from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass
class LLMRequest:
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    stop: Optional[List[str]] = None


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class LLMClient(Protocol):
    def generate(self, req: LLMRequest) -> LLMResponse:
        ...
