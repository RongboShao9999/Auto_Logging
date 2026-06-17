from __future__ import annotations

from typing import Any

from .planner import Planner
from .report import generate_report
from .tools import ComponentRegistry
from .types import ExecutionEvent, Plan, ToolResult


class Executor:
    def __init__(self, planner: Planner, registry: ComponentRegistry):
        self.planner = planner
        self.registry = registry

    def execute(
        self,
        plan: Plan,
        records: list[dict[str, Any]],
        report_metadata: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str, list[ExecutionEvent]]:
        current = records
        events: list[ExecutionEvent] = []
        extended_missing = False
        for task in plan.tasks:
            if task.condition == "extended_missing" and not extended_missing:
                result = ToolResult("success", current, {"skipped": True, "reason": "no extended missing intervals"})
            elif task.component == "report":
                report = generate_report(
                    plan.well_id,
                    current,
                    [event.to_dict() for event in events],
                    report_metadata,
                )
                result = ToolResult("success", report)
            else:
                result = self.registry.invoke(task.component, records=current, well_id=plan.well_id)
            command = {"well_id": plan.well_id, "dependencies": task.dependencies, "validation": task.validation}
            if task.component == "quality_control":
                extended_missing = bool((result.data or {}).get("extended_missing"))
            elif isinstance(result.data, list):
                current = result.data
            decision = self.planner.review(task, result)
            event = ExecutionEvent(task.id, task.name, task.component, command, result, decision)
            events.append(event)
            if decision == "expert_review":
                event.result.suggestion = event.result.suggestion or "Expert review required before deployment use"
            if task.component == "report":
                return current, str(result.data), events
        raise RuntimeError("Plan did not contain a report task")
