import argparse
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def reconcile(data_dir, output_dir, tolerance_days=3):
    banks = read_csv(data_dir / "BankStatementLine.csv")
    batches = read_csv(data_dir / "SettlementBatch.csv")

    batch_by_id = {row["batch_id"]: row for row in batches}
    used_batches = set()
    matches = []
    exceptions = []

    def add_exception(bank_id, batch_id, issue, severity="high"):
        exceptions.append({
            "exception_id": f"REX-{len(exceptions) + 1:07d}",
            "bank_line_id": bank_id,
            "batch_id": batch_id,
            "exception_type": issue,
            "severity": severity,
            "status": "open",
        })

    for bank in banks:
        bank_id = bank["bank_line_id"]
        reference = bank["reference"]
        batch = batch_by_id.get(reference)

        if batch is None:
            add_exception(
                bank_id, "", "unmatched_bank_record", "medium"
            )
            continue

        if reference in used_batches:
            add_exception(
                bank_id, reference, "duplicate_bank_reference"
            )
            continue

        if bank["currency"] != batch["currency"]:
            add_exception(
                bank_id, reference, "currency_mismatch"
            )
            continue

        difference = (
            Decimal(bank["amount"]) - Decimal(batch["net_amount"])
        )

        if abs(difference) > Decimal("0.01"):
            add_exception(
                bank_id, reference, "amount_mismatch"
            )
            continue

        try:
            booking = date.fromisoformat(bank["booking_date"])
            settlement = date.fromisoformat(batch["settlement_date"])
            days_late = (booking - settlement).days
        except ValueError:
            days_late = 0

        if days_late > tolerance_days:
            add_exception(
                bank_id, reference, "delayed_settlement", "medium"
            )

        matches.append({
            "reconciliation_id": f"RREC-{len(matches) + 1:07d}",
            "bank_line_id": bank_id,
            "batch_id": reference,
            "match_status": "matched",
            "match_method": "reference_currency_amount",
            "amount_difference": f"{difference:.2f}",
            "days_after_settlement": str(days_late),
        })

        used_batches.add(reference)

    for batch in batches:
        if batch["batch_id"] not in used_batches:
            add_exception(
                "", batch["batch_id"], "unmatched_settlement", "medium"
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "ReconciliationMatch.csv", matches)
    write_csv(output_dir / "Exception.csv", exceptions)

    summary = {
        "bank_lines": len(banks),
        "settlement_batches": len(batches),
        "matched": len(matches),
        "exceptions": len(exceptions),
    }

    for exception in exceptions:
        issue = exception["exception_type"]
        summary[issue] = summary.get(issue, 0) + 1

    with (output_dir / "reconciliation_summary.txt").open(
        "w", encoding="utf-8"
    ) as file:
        for key, value in summary.items():
            file.write(f"{key}: {value}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Reconcile bank lines against settlement batches"
    )
    parser.add_argument("--data", type=Path, default=Path("data/generated"))
    parser.add_argument("--out", type=Path, default=Path("data/reconciliation"))
    parser.add_argument("--tolerance-days", type=int, default=3)
    args = parser.parse_args()

    summary = reconcile(args.data, args.out, args.tolerance_days)
    print("Reconciliation complete.")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
