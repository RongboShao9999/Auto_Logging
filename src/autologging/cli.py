from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .datasets import load_records
from .pipeline import AutoLogging


def load_csv(path: str | Path) -> list[dict[str, Any]]:
    return load_records(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Auto-Logging reference workflow")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("csv")
    run.add_argument("--well-id", required=True)
    run.add_argument("--request", default="Complete full-process logging interpretation")
    run.add_argument("--output", default="runs/latest")
    run.add_argument("--report-metadata", help="JSON file containing report header and sign-off metadata")
    run.add_argument("--well", help="Optional WELLNUM filter for SPWLA-style multi-well files")
    run.add_argument("--limit", type=int, help="Optional row limit for quick smoke runs")
    run.add_argument("--reference-only", action="store_true", help="Disable bundled model/dataset outputs")
    args = parser.parse_args()
    metadata = json.loads(Path(args.report_metadata).read_text(encoding="utf-8")) if args.report_metadata else None
    records = load_records(args.csv, well=args.well, limit=args.limit)
    result = AutoLogging(use_local_assets=not args.reference_only).run(
        args.well_id,
        records,
        args.request,
        args.output,
        metadata,
    )
    print(json.dumps({"output": str(Path(args.output).resolve()), "events": len(result["events"])}, indent=2))


if __name__ == "__main__":
    main()
