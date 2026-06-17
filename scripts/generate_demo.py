from __future__ import annotations

import csv
import math
from pathlib import Path


def main() -> None:
    path = Path("examples/demo_well.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["DEPTH", "AC", "CAL", "CNL", "DEN", "GR", "RT", "RXO", "SP"]
    rows = []
    for index in range(160):
        phase = index / 12
        gr = 70 + 55 * (math.sin(phase) > 0.45) + 8 * math.sin(phase)
        row = {
            "DEPTH": 2500 + index * 0.125,
            "AC": 230 + 0.35 * gr,
            "CAL": 20.5,
            "CNL": 0.12 + gr / 1000,
            "DEN": 2.62 - gr / 600,
            "GR": gr,
            "RT": 45 if gr < 90 else 4,
            "RXO": 8,
            "SP": -30 + gr / 5,
        }
        if 55 <= index <= 102:
            row["AC"] = ""
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(path.resolve())


if __name__ == "__main__":
    main()

