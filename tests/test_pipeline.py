from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autologging.pipeline import AutoLogging


def sample_records() -> list[dict]:
    rows = []
    for index in range(60):
        rows.append(
            {
                "DEPTH": 1000 + index * 0.125,
                "AC": None if 5 <= index <= 50 else 250.0,
                "CAL": 20.0,
                "CNL": 0.2,
                "DEN": 2.35,
                "GR": 60.0 if index < 30 else 140.0,
                "RT": 30.0 if index < 30 else 3.0,
                "RXO": 5.0,
                "SP": -20.0,
            }
        )
    return rows


class PipelineTest(unittest.TestCase):
    def test_end_to_end_and_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            result = AutoLogging().run("TEST-01", sample_records(), output_dir=directory)
            self.assertEqual(len(result["events"]), 7)
            self.assertEqual(result["events"][2]["result"]["metrics"]["remaining_missing"], 0)
            self.assertTrue(all("PHIF" in row and "FLUID" in row for row in result["records"]))
            self.assertTrue(all(0 <= row["VSH"] <= 1 and 0 <= row["SW"] <= 1 for row in result["records"]))
            self.assertTrue(all("planner_decision" in event for event in result["events"]))
            self.assertTrue(Path(directory, "run.json").exists())
            self.assertIn("Interpretation Report", result["report"])

    def test_plan_dependencies(self):
        plan = AutoLogging().planner.create_plan("A", "Interpret porosity and fluid")
        by_id = {task.id: task for task in plan.tasks}
        self.assertIn("lithology", by_id["parameters"].dependencies)
        self.assertIn("parameters", by_id["fluid"].dependencies)


if __name__ == "__main__":
    unittest.main()
