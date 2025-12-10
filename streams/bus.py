from __future__ import annotations

import asyncio
from typing import Any, Dict, Set


class StreamBus:
    """Lightweight in-process pub/sub for live telemetry."""

    def __init__(self, max_queue: int = 0):
        self._subscribers: Set[asyncio.Queue] = set()
        self._max_queue = max_queue

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def publish(self, message: Dict[str, Any]) -> None:
        if not self._subscribers:
            return
        await asyncio.gather(*(subscriber.put(message) for subscriber in list(self._subscribers)))

    def subscriber_count(self) -> int:
        return len(self._subscribers)
