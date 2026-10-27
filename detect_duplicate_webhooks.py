import csv
from collections import defaultdict
from pathlib import Path

INPUT = Path("data/generated/ProcessorEvent.csv")
OUTPUT = Path("data/reconciliation/duplicate_webhooks.csv")


def main():
    groups = defaultdict(list)

    with INPUT.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = row.get("idempotency_key", "").strip()
            if key:
                groups[key].append(row)

    duplicates = []

    for key, rows in groups.items():
        # Repeated idempotency keys indicate possible duplicate delivery.
        if len(rows) > 1:
            for row in rows:
                duplicates.append({
                    "idempotency_key": key,
                    "processor_event_id": row["processor_event_id"],
                    "attempt_id": row["attempt_id"],
                    "ingest_status": row["ingest_status"],
                    "issue_type": row["issue_type"],
                    "duplicate_count": len(rows),
                })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "idempotency_key",
        "processor_event_id",
        "attempt_id",
        "ingest_status",
        "issue_type",
        "duplicate_count",
    ]

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(duplicates)

    print(f"Duplicate webhook rows found: {len(duplicates)}")
    print(f"Report saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
