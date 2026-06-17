from __future__ import annotations

import math
import os
import unittest
from unittest.mock import patch

from autologging.cloud import (
    CloudConfigurationError,
    CloudSettings,
    MODEL_ROUTES,
    parse_csv_records,
    prepare_matrix,
)


class CloudAdapterTest(unittest.TestCase):
    def test_requires_credentials_from_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CloudConfigurationError):
                CloudSettings.from_env()

    def test_parameter_route_prepares_log_resistivity(self):
        row = {"DEN": 2.4, "GR": 80, "NEU": 0.2, "PEF": 3, "RDEP": 100, "RMED": 10}
        matrix = prepare_matrix([row], MODEL_ROUTES["parameters"])
        self.assertEqual(matrix[-2:], [2.0, 1.0])

    def test_lithology_route_is_not_parameter_copy(self):
        route = MODEL_ROUTES["lithology"]
        self.assertEqual(len(route.features), 8)
        self.assertIn("LITHOLOGY", route.outputs)
        self.assertNotIn("PHIF", route.outputs)

    def test_csv_filter_and_missing_marker(self):
        content = b"WELLNUM,DEPTH,GR\n1,1000,80\n2,1001,-9999\n"
        records = parse_csv_records(content, 2)
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]["GR"])
        self.assertTrue(math.isclose(records[0]["DEPTH"], 1001))


if __name__ == "__main__":
    unittest.main()
