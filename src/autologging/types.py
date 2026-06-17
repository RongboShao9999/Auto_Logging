from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Task:
    id: str
    name: str
    component: str
    dependencies: list[str] = field(default_factory=list)
    condition: str | None = None
    validation: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    well_id: str
    request: str
    retrieved_rules: list[dict[str, Any]]
    tasks: list[Task]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolResult:
    status: str
    data: Any
    metrics: dict[str, Any] = field(default_factory=dict)
    abnormalities: list[str] = field(default_factory=list)
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionEvent:
    task_id: str
    task_name: str
    component: str
    command: dict[str, Any]
    result: ToolResult
    planner_decision: str = "continue"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["result"] = self.result.to_dict()
        return value
