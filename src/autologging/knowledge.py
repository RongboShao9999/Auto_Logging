from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_KNOWLEDGE = Path(__file__).resolve().parents[2] / "knowledge" / "rules.json"


class KnowledgeBase:
    def __init__(self, path: str | Path = DEFAULT_KNOWLEDGE):
        self.path = Path(path)
        self.data: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))

    def retrieve(self, request: str) -> list[dict[str, Any]]:
        query = request.lower()
        matches = [
            rule
            for rule in self.data["workflow_rules"]
            if any(keyword.lower() in query for keyword in rule["keywords"])
        ]
        return matches or self.data["workflow_rules"][:2]

    @property
    def curve_ranges(self) -> dict[str, list[float]]:
        return self.data["curve_ranges"]

    @property
    def parameter_ranges(self) -> dict[str, list[float]]:
        return self.data["parameter_ranges"]

    @property
    def thresholds(self) -> dict[str, float]:
        return self.data["thresholds"]

