from __future__ import annotations

from .knowledge import KnowledgeBase
from .types import Plan, Task, ToolResult


class Planner:
    """Dependency-aware planner grounded by the local rule knowledge base."""

    def __init__(self, knowledge: KnowledgeBase):
        self.knowledge = knowledge

    def create_plan(self, well_id: str, request: str) -> Plan:
        tasks = [
            Task("qc", "Data Quality Control", "quality_control"),
            Task("preprocess", "Data Preprocessing", "preprocess", ["qc"]),
            Task(
                "impute",
                "Extended Missing-Curve Imputation",
                "impute",
                ["preprocess"],
                condition="extended_missing",
            ),
            Task("lithology", "Lithology Identification", "lithology", ["preprocess", "impute"]),
            Task(
                "parameters",
                "Reservoir Parameter Prediction",
                "reservoir_parameters",
                ["lithology"],
                validation={"physical_ranges": True},
            ),
            Task("fluid", "Fluid Identification", "fluid", ["parameters"]),
            Task("report", "Interpretation Report", "report", ["lithology", "parameters", "fluid"]),
        ]
        return Plan(well_id, request, self.knowledge.retrieve(request), tasks)

    def review(self, task: Task, result: ToolResult) -> str:
        if result.status == "success":
            return "continue"
        if task.component == "impute":
            return "fallback"
        return "expert_review"

