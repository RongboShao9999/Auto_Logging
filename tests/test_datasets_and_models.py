from __future__ import annotations

import unittest
from pathlib import Path

from autologging.datasets import COLUMN_ALIASES, load_records, normalize_record
from autologging.local_models import DEFAULT_MODEL_DIR, ModelCatalog
from autologging.pipeline import AutoLogging


ROOT = Path(__file__).resolve().parents[1]


class DatasetAndModelAssetsTest(unittest.TestCase):
    def test_spwla_columns_and_missing_markers_are_normalized(self):
        record = normalize_record(
            {
                "DEPTH": 1000,
                "DTC": 80,
                "CALI": 8.5,
                "NEU": 0.2,
                "RDEP": 10,
                "RMED": "-9999",
                "PHIF": 0.18,
            }
        )
        self.assertEqual(record["AC"], 80)
        self.assertEqual(record["CAL"], 8.5)
        self.assertEqual(record["CNL"], 0.2)
        self.assertEqual(record["RT"], 10)
        self.assertEqual(record["PHIF"], 0.18)

    def test_dataset_aliases_match_reference_files(self):
        self.assertEqual(COLUMN_ALIASES["DTC"], "AC")
        self.assertEqual(COLUMN_ALIASES["CALI"], "CAL")
        self.assertEqual(COLUMN_ALIASES["NEU"], "CNL")
        self.assertEqual(COLUMN_ALIASES["RDEP"], "RT")
        self.assertEqual(COLUMN_ALIASES["RMED"], "RXO")
        self.assertEqual(COLUMN_ALIASES["POR"], "PHIF")
        self.assertEqual(COLUMN_ALIASES["POR_multi"], "PHIF_MODEL")

    def test_forward_dataset_percent_parameters_are_fractional(self):
        records = load_records(ROOT / "forward_dataset" / "data_test_18.csv", limit=3)
        self.assertIn("DEPTH", records[0])
        self.assertLess(records[0]["VSH_MODEL"], 1)
        self.assertLess(records[0]["PHIF_MODEL"], 1)
        self.assertLess(records[0]["SW_MODEL"], 1)
        self.assertEqual(records[0]["LITHOLOGY_MODEL"], "Shale")
        self.assertEqual(records[0]["FLUID_MODEL"], "Non-Reservoir")

    def test_spwla_well_filter_accepts_integer_text(self):
        records = load_records(ROOT / "SPWLA_dataset" / "test.csv", well="100", limit=2)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["WELLNUM"], 100)

    def test_model_catalog_reports_bundled_assets(self):
        catalog = ModelCatalog(DEFAULT_MODEL_DIR).describe()
        self.assertTrue(catalog["available"])
        self.assertIn("conclusion_KNN.pkl", catalog["sklearn_models"])
        self.assertTrue(any(name.endswith("saved_model.pb") for name in catalog["tensorflow_models"]))

    def test_pipeline_uses_forward_dataset_model_outputs(self):
        records = load_records(ROOT / "forward_dataset" / "data_test_18.csv", limit=10)
        result = AutoLogging().run("FORWARD-18", records)
        self.assertEqual(
            result["events"][3]["result"]["metrics"]["model"],
            "bundled-forward-dataset-labels",
        )
        self.assertEqual(
            result["events"][4]["result"]["metrics"]["model"],
            "bundled-dataset-reservoir-parameters",
        )
        self.assertEqual(
            result["events"][5]["result"]["metrics"]["model"],
            "bundled-forward-dataset-fluid-labels",
        )


if __name__ == "__main__":
    unittest.main()
