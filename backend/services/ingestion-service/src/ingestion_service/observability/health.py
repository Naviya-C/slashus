from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HealthRegistry:
    consumer_running: bool = False
    shutting_down: bool = False

    @property
    def ready(self) -> bool:
        return self.consumer_running and not self.shutting_down

