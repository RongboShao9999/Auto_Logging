from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .executor import Executor
from .knowledge import KnowledgeBase
from .local_models import DEFAULT_MODEL_DIR, LocalAssetTools, ModelCatalog
from .planner import Planner
from .report import build_report
from .tools import ComponentRegistry, ReferenceTools


class AutoLogging:
    def __init__(
        self,
        knowledge_path: str | Path | None = None,
        model_dir: str | Path | None = DEFAULT_MODEL_DIR,
        use_local_assets: bool = True,
    ):
        knowledge = KnowledgeBase(knowledge_path) if knowledge_path else KnowledgeBase()
        catalog = ModelCatalog(model_dir) if model_dir else None
        tools = (
            LocalAssetTools(knowledge, model_dir)
            if use_local_assets and catalog is not None and catalog.available()
            else ReferenceTools(knowledge)
        )
        registry = ComponentRegistry()
        for name in ("quality_control", "preprocess", "impute", "lithology", "reservoir_parameters", "fluid"):
            registry.register(name, getattr(tools, name))
        if isinstance(tools, LocalAssetTools):
            registry.register("model_catalog", tools.catalog_result)
        self.planner = Planner(knowledge)
        self.executor = Executor(self.planner, registry)
        self.model_catalog = catalog.describe() if catalog else None

    def run(
        self,
        well_id: str,
        records: list[dict[str, Any]],
        request: str = "Complete full-process logging interpretation",
        output_dir: str | Path | None = None,
        report_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plan = self.planner.create_plan(well_id, request)
        final_records, report, events = self.executor.execute(plan, records, report_metadata)
        report_package = build_report(
            well_id, final_records, [event.to_dict() for event in events], report_metadata
        )
        report = report_package["markdown"]
        run = {
            "well_id": well_id,
            "request": request,
            "plan": plan.to_dict(),
            "model_catalog": self.model_catalog,
            "events": [event.to_dict() for event in events],
            "records": final_records,
            "report": report,
            "report_compliance": {
                key: report_package[key]
                for key in ("standard", "metadata", "missing_required_fields", "sections")
            },
        }
        if output_dir:
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            (path / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
            (path / "report.md").write_text(report, encoding="utf-8")
            (path / "report.json").write_text(
                json.dumps(run["report_compliance"], ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return run
