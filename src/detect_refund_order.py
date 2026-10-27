import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

INPUT = Path("data/generated/ProcessorEvent.csv")
OUTPUT = Path("data/reconciliation/refunds_before_capture.csv")


def main():
    events_by_attempt = defaultdict(list)

    with INPUT.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["event_status"] == "succeeded":
                events_by_attempt[row["attempt_id"]].append(row)

    anomalies = []

    for attempt_id, events in events_by_attempt.items():
        captures = [
            e for e in events
            if e["event_type"].lower() == "capture"
        ]
        refunds = [
            e for e in events
            if e["event_type"].lower() == "refund"
        ]

        for refund in refunds:
            refund_time = datetime.fromisoformat(refund["event_at"])

            # A refund is suspicious if no successful capture occurred
            # at or before the refund time for this attempt.
            earlier_captures = [
                c for c in captures
                if datetime.fromisoformat(c["event_at"]) <= refund_time
            ]

            if not earlier_captures:
                anomalies.append({
                    "attempt_id": attempt_id,
                    "refund_event_id": refund["processor_event_id"],
                    "refund_time": refund["event_at"],
                    "refund_amount": refund["amount"],
                    "capture_found_before_refund": "no",
                    "issue_type": "refund_before_capture",
                })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "attempt_id",
        "refund_event_id",
        "refund_time",
        "refund_amount",
        "capture_found_before_refund",
        "issue_type",
    ]

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(anomalies)

    print(f"Refund-before-capture anomalies found: {len(anomalies)}")
    print(f"Report saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
