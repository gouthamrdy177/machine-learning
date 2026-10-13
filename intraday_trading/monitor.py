from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class MonitoringEvent:
    timestamp: str
    category: str
    message: str
    metrics: Dict[str, float] = field(default_factory=dict)


class Monitor:
    def __init__(self):
        self.events: List[MonitoringEvent] = []
        self.killed = False

    def emit(self, category: str, message: str, metrics: Dict[str, float] | None = None) -> None:
        self.events.append(
            MonitoringEvent(
                timestamp=datetime.utcnow().isoformat(),
                category=category,
                message=message,
                metrics=metrics or {},
            )
        )

    def kill_switch(self, reason: str) -> None:
        self.killed = True
        self.emit("KILL_SWITCH", reason)
