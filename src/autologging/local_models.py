from __future__ import annotations

import importlib.util
import math
import warnings
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .knowledge import KnowledgeBase
from .tools import ReferenceTools, is_number
from .types import ToolResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = PROJECT_ROOT / "model"

LITHOLOGY_FEATURES = ("DEN", "AC", "CNL", "RT", "RXO", "GR", "SP")
FLUID_FEATURES = ("GR", "DEN", "CNL", "RT", "RXO", "SP", "PHIF", "SW")

LITHOLOGY_LABELS = {
    "Shale": "mudstone",
    "Mudstone": "mudstone",
    "Siltstone": "siltstone",
    "Fine Sandstone": "fine_sandstone",
    "Medium Sandstone": "medium_sandstone",
}

FLUID_LABELS = {
    "Oil Layer": "oil",
    "Oil-Water Layer": "oil_water",
    "Oil-Bearing Water Layer": "oil_bearing_water",
    "Water Layer": "water",
    "Dry Layer": "dry",
    "Non-Reservoir": "non_reservoir",
}


def _normal_label(value: Any, mapping: dict[str, str]) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return mapping.get(text, text.lower().replace(" ", "_").replace("-", "_"))


def _fraction(value: Any) -> float | None:
    if not is_number(value):
        return None
    number = float(value)
    return number / 100.0 if number > 1.5 else number


def _confidence(model: Any, matrix: list[list[float]]) -> list[float]:
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(matrix)
        return [float(max(row)) for row in probabilities]
    return [1.0 for _ in matrix]


class ModelCatalog:
    def __init__(self, root: str | Path = DEFAULT_MODEL_DIR):
        self.root = Path(root)

    def available(self) -> bool:
        return self.root.exists()

    def has_tensorflow(self) -> bool:
        return importlib.util.find_spec("tensorflow") is not None

    def has_sklearn(self) -> bool:
        return importlib.util.find_spec("sklearn") is not None and importlib.util.find_spec("joblib") is not None

    def tensorflow_models(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(str(path.relative_to(self.root)) for path in self.root.glob("*/saved_model.pb"))

    def sklearn_models(self) -> list[str]:
        sklearn_dir = self.root / "sklearn_model"
        if not sklearn_dir.exists():
            return []
        return sorted(path.name for path in sklearn_dir.glob("*.pkl"))

    def describe(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "available": self.available(),
            "tensorflow_available": self.has_tensorflow(),
            "sklearn_available": self.has_sklearn(),
            "tensorflow_models": self.tensorflow_models(),
            "sklearn_models": self.sklearn_models(),
        }

    def load_sklearn(self, name: str) -> Any:
        if not self.has_sklearn():
            raise RuntimeError("scikit-learn/joblib is not available")
        import joblib

        path = self.root / "sklearn_model" / name
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return joblib.load(path)


class LocalAssetTools(ReferenceTools):
    """Use bundled datasets/model outputs where possible, then fall back to reference physics rules."""

    def __init__(self, knowledge: KnowledgeBase, model_dir: str | Path = DEFAULT_MODEL_DIR):
        super().__init__(knowledge)
        self.catalog = ModelCatalog(model_dir)
        self._model_cache: dict[str, Any] = {}

    def _load_model(self, name: str) -> Any:
        if name not in self._model_cache:
            self._model_cache[name] = self.catalog.load_sklearn(name)
        return self._model_cache[name]

    def catalog_result(self, **_: Any) -> ToolResult:
        return ToolResult("success", self.catalog.describe())

    def lithology(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        from_dataset = 0
        for row in output:
            label = _normal_label(row.get("LITHOLOGY_MODEL") or row.get("LITHOLOGY_TRUE"), LITHOLOGY_LABELS)
            if label:
                row["LITHOLOGY"] = label
                row["LITHOLOGY_CONFIDENCE"] = 1.0
                from_dataset += 1
        if from_dataset == len(output):
            counts = Counter(row["LITHOLOGY"] for row in output)
            return ToolResult(
                "success",
                output,
                {"class_counts": dict(counts), "model": "bundled-forward-dataset-labels", "source_records": from_dataset},
            )

        if self.catalog.has_sklearn() and (self.catalog.root / "sklearn_model" / "layer_MLP.pkl").exists():
            matrix: list[list[float]] = []
            rows: list[dict[str, Any]] = []
            for row in output:
                if all(is_number(row.get(feature)) for feature in LITHOLOGY_FEATURES):
                    matrix.append([float(row[feature]) for feature in LITHOLOGY_FEATURES])
                    rows.append(row)
            if rows:
                try:
                    model = self._load_model("layer_MLP.pkl")
                    predictions = model.predict(matrix)
                    confidences = _confidence(model, matrix)
                    for row, value, confidence in zip(rows, predictions, confidences):
                        row["LITHOLOGY_MODEL_CLASS"] = int(value)
                        row["LITHOLOGY_CONFIDENCE"] = round(confidence, 6)
                    fallback = super().lithology(output).data
                    for row, fallback_row in zip(output, fallback):
                        row["LITHOLOGY"] = row.get("LITHOLOGY") or fallback_row["LITHOLOGY"]
                    counts = Counter(row["LITHOLOGY"] for row in output)
                    return ToolResult(
                        "success",
                        output,
                        {
                            "class_counts": dict(counts),
                            "model": "layer_MLP.pkl+reference-label-decoder",
                            "model_class_counts": dict(Counter(row.get("LITHOLOGY_MODEL_CLASS") for row in rows)),
                        },
                    )
                except Exception as exc:
                    result = super().lithology(records)
                    result.metrics["local_model_error"] = str(exc)
                    result.metrics["model"] = "reference-rule-classifier"
                    return result
        return super().lithology(records)

    def reservoir_parameters(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        filled = 0
        for row in output:
            vsh = _fraction(row.get("VSH_MODEL", row.get("VSH")))
            phif = _fraction(row.get("PHIF_MODEL", row.get("PHIF")))
            sw = _fraction(row.get("SW_MODEL", row.get("SW")))
            if vsh is not None and phif is not None and sw is not None:
                row.update({"VSH": round(vsh, 6), "PHIF": round(phif, 6), "SW": round(sw, 6)})
                filled += 1
        if filled == len(output):
            return ToolResult(
                "success",
                output,
                {"model": "bundled-dataset-reservoir-parameters", "source_records": filled},
            )
        return super().reservoir_parameters(output)

    def fluid(self, records: list[dict[str, Any]], **_: Any) -> ToolResult:
        output = deepcopy(records)
        from_dataset = 0
        for row in output:
            label = _normal_label(row.get("FLUID_MODEL") or row.get("FLUID_TRUE"), FLUID_LABELS)
            if label:
                row["FLUID"] = label
                row["FLUID_CONFIDENCE"] = 1.0
                from_dataset += 1
        if from_dataset == len(output):
            counts = Counter(row["FLUID"] for row in output)
            return ToolResult(
                "success",
                output,
                {"class_counts": dict(counts), "model": "bundled-forward-dataset-fluid-labels", "source_records": from_dataset},
            )

        if self.catalog.has_sklearn() and (self.catalog.root / "sklearn_model" / "conclusion_KNN.pkl").exists():
            matrix: list[list[float]] = []
            rows: list[dict[str, Any]] = []
            for row in output:
                values: list[float] = []
                for feature in FLUID_FEATURES:
                    value = row.get(feature)
                    if not is_number(value):
                        break
                    values.append(math.log10(float(value)) if feature in {"RT", "RXO"} and float(value) > 0 else float(value))
                else:
                    matrix.append(values)
                    rows.append(row)
            if rows:
                try:
                    model = self._load_model("conclusion_KNN.pkl")
                    predictions = model.predict(matrix)
                    confidences = _confidence(model, matrix)
                    for row, value, confidence in zip(rows, predictions, confidences):
                        row["FLUID_MODEL_CLASS"] = int(value)
                        row["FLUID_CONFIDENCE"] = round(confidence, 6)
                    fallback = super().fluid(output).data
                    for row, fallback_row in zip(output, fallback):
                        row["FLUID"] = row.get("FLUID") or fallback_row["FLUID"]
                    counts = Counter(row["FLUID"] for row in output)
                    return ToolResult(
                        "success",
                        output,
                        {
                            "class_counts": dict(counts),
                            "model": "conclusion_KNN.pkl+reference-label-decoder",
                            "model_class_counts": dict(Counter(row.get("FLUID_MODEL_CLASS") for row in rows)),
                        },
                    )
                except Exception as exc:
                    result = super().fluid(records)
                    result.metrics["local_model_error"] = str(exc)
                    result.metrics["model"] = "reference-fluid-rules"
                    return result
        return super().fluid(records)
