import asyncio
from typing import Dict, List, Callable, Any, Awaitable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    type: str
    payload: Any
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event):
        await self._queue.put(event)

    async def start(self):
        self._running = True
        while self._running:
            try:
                event = await self._queue.get()
                if event.type in self._subscribers:
                    handlers = self._subscribers[event.type]
                    # Execute handlers concurrently
                    await asyncio.gather(*[h(event) for h in handlers])
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing event {event.type}: {e}")

    def stop(self):
        self._running = False
