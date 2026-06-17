from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FieldNameAuditTest(unittest.TestCase):
    def test_porosity_field_uses_phif_not_phi(self):
        forbidden = re.compile(r"\b" + "PH" + "I" + r"\b")
        files = [
            *ROOT.joinpath("src").rglob("*.py"),
            ROOT / "knowledge" / "rules.json",
            ROOT / "README.md",
        ]
        offenders = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            if forbidden.search(text):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
