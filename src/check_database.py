import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "payment_reconciliation.db"

def main():
    if not DB_PATH.exists():
        print("ERROR: Database not found. Run python .\src\load_database.py first.")
        raise SystemExit(1)

    with sqlite3.connect(DB_PATH) as conn:
        checks = [
            ("Bank statement rows", "SELECT COUNT(*) FROM bank_statement_lines"),
            ("Settlement batches", "SELECT COUNT(*) FROM settlement_batches"),
            ("Reconciliation matches", "SELECT COUNT(*) FROM reconciliation_matches"),
            ("Reconciliation exceptions", "SELECT COUNT(*) FROM reconciliation_exceptions"),
            ("Duplicate settlement-line flags", "SELECT COUNT(*) FROM duplicate_settlement_lines"),
            ("Duplicate webhook flags", "SELECT COUNT(*) FROM duplicate_webhooks"),
            ("Refund-before-capture flags", "SELECT COUNT(*) FROM refunds_before_capture"),
        ]

        print("\nDATABASE QUALITY CHECKS")
        print("-" * 40)

        for label, query in checks:
            try:
                count = conn.execute(query).fetchone()[0]
                print(f"{label}: {count:,}")
            except sqlite3.Error as error:
                print(f"CHECK FAILED: {label}: {error}")

        print(f"\nDatabase: {DB_PATH}")

if __name__ == "__main__":
    main()
