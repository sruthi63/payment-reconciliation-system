import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_duplicate_settlement_lines_are_detected():
    result = subprocess.run(
        [sys.executable, str(ROOT / "src" / "detect_duplicates.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    report = ROOT / "data" / "reconciliation" / "duplicate_settlement_lines.csv"
    with report.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["processor_event_id"] == rows[1]["processor_event_id"]
    assert rows[0]["amount"] == rows[1]["amount"]
    assert rows[0]["duplicate_count"] == "2"
    assert "Duplicate processor events found: 2" in result.stdout
