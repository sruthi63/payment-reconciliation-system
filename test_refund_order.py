import csv
import subprocess
import sys
from pathlib import Path


def test_planted_refund_before_capture_is_detected():
    result = subprocess.run(
        [sys.executable, "src/detect_refund_order.py"],
        capture_output=True,
        text=True,
        check=True,
    )

    report = Path("data/reconciliation/refunds_before_capture.csv")
    with report.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    planted = [
        row for row in rows
        if row["refund_event_id"] == "EVT-ANOM-REFUND-0001"
    ]

    assert planted, "Planted refund-before-capture anomaly was not detected"
    assert planted[0]["issue_type"] == "refund_before_capture"
    assert planted[0]["capture_found_before_refund"] == "no"
    assert "Refund-before-capture anomalies found:" in result.stdout
