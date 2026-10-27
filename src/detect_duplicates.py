import csv
from collections import defaultdict
from pathlib import Path

INPUT = Path("data/generated/SettlementLine.csv")
OUTPUT = Path("data/reconciliation/duplicate_settlement_lines.csv")


def main():
    groups = defaultdict(list)

    with INPUT.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            groups[row["processor_event_id"]].append(row)

    duplicates = []
    for event_id, rows in groups.items():
        if len(rows) > 1:
            for row in rows:
                duplicates.append({
                    "processor_event_id": event_id,
                    "settlement_line_id": row["settlement_line_id"],
                    "batch_id": row["batch_id"],
                    "amount": row["amount"],
                    "duplicate_count": len(rows),
                })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "processor_event_id",
            "settlement_line_id",
            "batch_id",
            "amount",
            "duplicate_count",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(duplicates)

    print(f"Duplicate processor events found: {len(duplicates)}")
    print(f"Report saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
