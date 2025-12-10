from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .base import LLMClient, LLMRequest, LLMResponse


@dataclass
class LLMRouter:
    clients: Dict[str, LLMClient]
    default_backend: Optional[str] = None

    def generate(self, req: LLMRequest, backend: Optional[str] = None) -> Tuple[LLMResponse, str]:
        name = backend or self.default_backend
        if not name or name not in self.clients:
            raise RuntimeError(f"LLM backend '{name}' is not configured")
        client = self.clients[name]
        return client.generate(req), name
