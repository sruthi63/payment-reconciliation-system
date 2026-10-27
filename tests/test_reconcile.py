import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reconcile import reconcile


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_reconcile_match_and_exceptions(tmp_path):
    data = tmp_path / "input"
    output = tmp_path / "output"
    data.mkdir()

    write_csv(data / "SettlementBatch.csv", [
        {
            "batch_id": "SET-1",
            "currency": "INR",
            "net_amount": "100.00",
            "settlement_date": "2026-01-01",
        },
        {
            "batch_id": "SET-2",
            "currency": "USD",
            "net_amount": "200.00",
            "settlement_date": "2026-01-01",
        },
        {
            "batch_id": "SET-3",
            "currency": "EUR",
            "net_amount": "300.00",
            "settlement_date": "2026-01-01",
        },
    ])

    write_csv(data / "BankStatementLine.csv", [
        {
            "bank_line_id": "BANK-1",
            "reference": "SET-1",
            "amount": "100.00",
            "currency": "INR",
            "booking_date": "2026-01-01",
            "value_date": "2026-01-01",
        },
        {
            "bank_line_id": "BANK-2",
            "reference": "SET-2",
            "amount": "200.00",
            "currency": "ZZZ",
            "booking_date": "2026-01-01",
            "value_date": "2026-01-01",
        },
        {
            "bank_line_id": "BANK-3",
            "reference": "SET-3",
            "amount": "301.00",
            "currency": "EUR",
            "booking_date": "2026-01-01",
            "value_date": "2026-01-01",
        },
        {
            "bank_line_id": "BANK-4",
            "reference": "SET-MISSING",
            "amount": "50.00",
            "currency": "INR",
            "booking_date": "2026-01-01",
            "value_date": "2026-01-01",
        },
    ])

    summary = reconcile(data, output)

    with (output / "ReconciliationMatch.csv").open(
        newline="", encoding="utf-8"
    ) as f:
        matches = list(csv.DictReader(f))

    with (output / "Exception.csv").open(
        newline="", encoding="utf-8"
    ) as f:
        exceptions = list(csv.DictReader(f))

    assert summary["matched"] == 1
    assert len(matches) == 1
    assert matches[0]["batch_id"] == "SET-1"

    issue_types = {row["exception_type"] for row in exceptions}
    assert "currency_mismatch" in issue_types
    assert "amount_mismatch" in issue_types
    assert "unmatched_bank_record" in issue_types
    assert "unmatched_settlement" in issue_types
