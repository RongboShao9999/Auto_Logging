from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any


MISSING_MARKERS = {"", "-9999", "-9999.0", "nan", "NaN", "NULL", "None"}

COLUMN_ALIASES = {
    "#DEPTH": "DEPTH",
    "CALI": "CAL",
    "NEU": "CNL",
    "DTC": "AC",
    "RDEP": "RT",
    "RMED": "RXO",
    "PHIF": "PHIF",
    "POR": "PHIF",
    "Vsh": "VSH",
    "Vsh_multi": "VSH_MODEL",
    "POR_multi": "PHIF_MODEL",
    "Sw": "SW",
    "Sw_multi": "SW_MODEL",
    "lithology_CNN": "LITHOLOGY_MODEL",
    "lithology": "LITHOLOGY_TRUE",
    "Fluid_KNN": "FLUID_MODEL",
    "CASE": "FLUID_TRUE",
}

FRACTION_FIELDS = {"CNL", "PHIF", "PHIF_MODEL", "VSH", "VSH_MODEL", "SW", "SW_MODEL"}


def _parse_value(value: str | None) -> Any:
    if value is None or value.strip() in MISSING_MARKERS:
        return None
    text = value.strip()
    try:
        number = float(text)
    except ValueError:
        return text
    return number if math.isfinite(number) else None


def _as_fraction(key: str, value: Any) -> Any:
    if key not in FRACTION_FIELDS or not isinstance(value, (int, float)):
        return value
    number = float(value)
    return number / 100.0 if number > 1.5 else number


def normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    aliases_used: dict[str, str] = {}
    for original_key, value in row.items():
        key = COLUMN_ALIASES.get(original_key, original_key)
        if key in normalized and normalized[key] is not None:
            aliases_used.setdefault("_ALIASES", "")
            aliases_used["_ALIASES"] += f"{original_key}->{key};"
            continue
        normalized[key] = _as_fraction(key, value)
    normalized.update(aliases_used)
    return normalized


def _same_well(left: Any, right: int | str) -> bool:
    if left is None:
        return False
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return str(left) == str(right)


def load_records(path: str | Path, well: int | str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    source = Path(path)
    delimiter = "\t" if source.suffix.lower() == ".txt" else ","
    records: list[dict[str, Any]] = []
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            parsed = {key: _parse_value(value) for key, value in row.items() if key is not None}
            if well is not None and parsed.get("WELLNUM") is not None and not _same_well(parsed["WELLNUM"], well):
                continue
            records.append(normalize_record(parsed))
            if limit is not None and len(records) >= limit:
                break
    if not records:
        raise ValueError(f"No records loaded from {source}")
    return records


def detect_dataset(path: str | Path) -> str:
    parts = {part.lower() for part in Path(path).parts}
    if "spwla_dataset" in parts:
        return "spwla"
    if "forward_dataset" in parts:
        return "forward"
    return "generic"
