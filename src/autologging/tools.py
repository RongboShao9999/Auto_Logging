from __future__ import annotations

import math
from collections import Counter
from copy import deepcopy
from typing import Any, Callable

from .knowledge import KnowledgeBase
from .types import ToolResult

CURVES = ("AC", "CAL", "CNL", "DEN", "GR", "RT", "RXO", "SP")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def interpolate(records: list[dict[str, Any]], curve: str, max_gap: int | None = None) -> int:
    changed = 0
    index = 0
    while index < len(records):
        if is_number(records[index].get(curve)):
            index += 1
            continue
        start = index
        while index < len(records) and not is_number(records[index].get(curve)):
            index += 1
        end = index
        length = end - start
        if max_gap is not None and length > max_gap:
            continue
        left = records[start - 1].get(curve) if start > 0 else None
        right = records[end].get(curve) if end < len(records) else None
        if not is_number(left) and not is_number(right):
            continue
        left = float(left if is_number(left) else right)
        right = float(right if is_number(right) else left)
        for offset, row_index in enumerate(range(start, end), 1):
            records[row_index][curve] = left + (right - left) * offset / (length + 1)
            changed += 1
    return changed


class ComponentRegistry:
    def __init__(self):
        self._components: dict[str, Callable[..., ToolResult]] = {}

    def register(self, name: str, component: Callable[..., ToolResult]) -> None:
        self._components[name] = component

    def invoke(self, name: str, **kwargs: Any) -> ToolResult:
        if name not in self._components:
            return ToolResult("failed", None, abnormalities=[f"Component unavailable: {name}"])
        return self._components[name](**kwargs)


class ReferenceTools:
    """Deterministic proxies for the paper's unpublished trained small models."""

    def __init__(self, knowledge: KnowledgeBase):
        self.knowledge = knowledge

    def quality_control(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        total = max(1, len(records) * len(CURVES))
        missing = outliers = 0
        extended: list[dict[str, Any]] = []
        limit = int(self.knowledge.thresholds["extended_missing_points"])
        for curve in CURVES:
            low, high = self.knowledge.curve_ranges[curve]
            run_start = None
            for index, row in enumerate(records + [{}]):
                value = row.get(curve)
                if index < len(records) and not is_number(value):
                    missing += 1
                    run_start = index if run_start is None else run_start
                else:
                    if run_start is not None and index - run_start > limit:
                        extended.append({"curve": curve, "start_index": run_start, "end_index": index - 1})
                    run_start = None
                    if index < len(records) and not low <= float(value) <= high:
                        outliers += 1
        depths = [float(row["DEPTH"]) for row in records if is_number(row.get("DEPTH"))]
        depth_monotonic = all(b > a for a, b in zip(depths, depths[1:]))
        ratio = outliers / total
        abnormalities = []
        if ratio >= self.knowledge.thresholds["max_outlier_ratio"]:
            abnormalities.append(f"Outlier ratio {ratio:.3f} exceeds threshold")
        if not depth_monotonic:
            abnormalities.append("Depth is not strictly increasing")
        return ToolResult(
            "abnormal" if abnormalities else "success",
            {"extended_missing": extended},
            {"outlier_ratio": ratio, "missing_values": missing, "depth_monotonic": depth_monotonic},
            abnormalities,
            "Run preprocessing and review depth ordering" if abnormalities else None,
        )

    def preprocess(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        corrected = filled = 0
        limit = int(self.knowledge.thresholds["extended_missing_points"])
        for curve in CURVES:
            low, high = self.knowledge.curve_ranges[curve]
            for row in output:
                value = row.get(curve)
                if is_number(value) and not low <= float(value) <= high:
                    row[curve] = None
                    corrected += 1
            filled += interpolate(output, curve, max_gap=limit)
        output.sort(key=lambda row: float(row.get("DEPTH", math.inf)))
        return ToolResult("success", output, {"outliers_removed": corrected, "sporadic_values_filled": filled})

    def impute(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        filled = sum(interpolate(output, curve) for curve in ("AC", "CNL", "RT"))
        remaining = sum(not is_number(row.get(curve)) for row in output for curve in ("AC", "CNL", "RT"))
        return ToolResult(
            "success" if remaining == 0 else "abnormal",
            output,
            {"imputed_values": filled, "remaining_missing": remaining, "model": "reference-linear-fallback"},
            [] if remaining == 0 else ["Some target curves could not be imputed"],
        )

    def lithology(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        counts: Counter[str] = Counter()
        for row in output:
            gr = float(row.get("GR") or 100)
            ac = float(row.get("AC") or 280)
            if gr >= 120:
                label = "mudstone"
            elif gr < 55 and ac < 250:
                label = "medium_sandstone"
            elif gr < 80:
                label = "fine_sandstone"
            else:
                label = "siltstone"
            row["LITHOLOGY"] = label
            counts[label] += 1
        return ToolResult("success", output, {"class_counts": dict(counts), "model": "reference-rule-classifier"})

    def reservoir_parameters(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        clipped = 0
        for row in output:
            gr = float(row.get("GR") or 100)
            den = float(row.get("DEN") or 2.45)
            rt = max(0.01, float(row.get("RT") or 1))
            vsh = clamp((gr - 30) / 120, 0, 1)
            phif = clamp(((2.65 - den) / 1.65) * (1 - 0.35 * vsh), 0, 0.45)
            sw = clamp(math.sqrt(1.0 / max(rt * max(phif, 0.02) ** 2, 1e-6)), 0, 1)
            row.update({"VSH": round(vsh, 6), "PHIF": round(phif, 6), "SW": round(sw, 6)})
            clipped += int(vsh in (0, 1)) + int(phif in (0, 0.45)) + int(sw in (0, 1))
        return ToolResult("success", output, {"physically_clipped_values": clipped, "model": "reference-petrophysics"})

    def fluid(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        counts: Counter[str] = Counter()
        for row in output:
            phif, sw, rt = float(row["PHIF"]), float(row["SW"]), float(row.get("RT") or 0)
            if phif < 0.06:
                label = "dry"
            elif sw > 0.75:
                label = "water"
            elif sw < 0.45 and rt > 10:
                label = "oil"
            else:
                label = "oil_bearing_water"
            row["FLUID"] = label
            counts[label] += 1
        return ToolResult("success", output, {"class_counts": dict(counts), "model": "reference-fluid-rules"})
