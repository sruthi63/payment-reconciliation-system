import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_duplicate_webhook_is_detected():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "src" / "detect_duplicate_webhooks.py"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    report = ROOT / "data" / "reconciliation" / "duplicate_webhooks.csv"

    with report.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["idempotency_key"] == rows[1]["idempotency_key"]
    assert rows[0]["attempt_id"] == rows[1]["attempt_id"]
    assert {row["ingest_status"] for row in rows} == {
        "accepted", "duplicate"
    }
    assert "Duplicate webhook rows found: 2" in result.stdout
