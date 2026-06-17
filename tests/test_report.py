from __future__ import annotations

import unittest

from autologging.report import STANDARD, ReportMetadata, build_report
from test_pipeline import sample_records


def interpreted_records():
    records = sample_records()
    for index, row in enumerate(records):
        row.update(
            {
                "LITHOLOGY": "fine_sandstone" if index < 30 else "mudstone",
                "FLUID": "oil" if index < 30 else "water",
                "VSH": 0.2 if index < 30 else 0.8,
                "PHIF": 0.18 if index < 30 else 0.08,
                "SW": 0.35 if index < 30 else 0.9,
            }
        )
    return records


class StandardReportTest(unittest.TestCase):
    def test_report_contains_standard_sections_and_layer_table(self):
        package = build_report(
            "A-1",
            interpreted_records(),
            [],
            {
                "oilfield": "测试油田",
                "well_type": "评价井",
                "operator": "甲方",
                "contractor": "乙方",
                "target_interval": "1000-1010 m",
                "interpreter": "编写人",
                "reviewer": "审核人",
            },
        )
        self.assertEqual(package["standard"], STANDARD)
        self.assertEqual(package["missing_required_fields"], [])
        self.assertIn("## 4 解释成果", package["markdown"])
        self.assertIn("|序号|顶深/m|底深/m|", package["markdown"])
        self.assertIn("油层", package["markdown"])

    def test_missing_metadata_is_explicit(self):
        package = build_report("A-1", interpreted_records(), [])
        self.assertIn("oilfield", package["missing_required_fields"])
        self.assertIn("报告状态：资料待补充", package["markdown"])

    def test_empty_records_rejected(self):
        with self.assertRaises(ValueError):
            build_report("A-1", [], [])

    def test_metadata_ignores_unknown_fields(self):
        metadata = ReportMetadata.from_dict("A-1", {"oilfield": "X", "unknown": "Y"})
        self.assertEqual(metadata.oilfield, "X")


if __name__ == "__main__":
    unittest.main()
