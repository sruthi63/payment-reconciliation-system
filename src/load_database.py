import csv
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
GENERATED = BASE / "data" / "generated"
REPORTS = BASE / "data" / "reconciliation"
DB_PATH = BASE / "data" / "payment_reconciliation.db"

TABLES = {
    "merchants": GENERATED / "Merchant.csv",
    "payment_orders": GENERATED / "PaymentOrder.csv",
    "payment_attempts": GENERATED / "PaymentAttempt.csv",
    "processor_events": GENERATED / "ProcessorEvent.csv",
    "settlement_batches": GENERATED / "SettlementBatch.csv",
    "settlement_lines": GENERATED / "SettlementLine.csv",
    "bank_statement_lines": GENERATED / "BankStatementLine.csv",
    "reconciliation_matches": REPORTS / "ReconciliationMatch.csv",
    "reconciliation_exceptions": REPORTS / "Exception.csv",
    "duplicate_settlement_lines": REPORTS / "duplicate_settlement_lines.csv",
    "duplicate_webhooks": REPORTS / "duplicate_webhooks.csv",
    "refunds_before_capture": REPORTS / "refunds_before_capture.csv",
}


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def load_csv(connection, table_name, csv_path):
    if not csv_path.exists():
        print(f"SKIPPED: {csv_path.name} not found")
        return

    with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        rows = list(reader)

    if not columns:
        print(f"SKIPPED: {csv_path.name} has no headers")
        return

    table = quote_identifier(table_name)
    column_definitions = ", ".join(
        f"{quote_identifier(column)} TEXT" for column in columns
    )

    connection.execute(f"DROP TABLE IF EXISTS {table}")
    connection.execute(
        f"CREATE TABLE {table} "
        f"(id INTEGER PRIMARY KEY AUTOINCREMENT, {column_definitions})"
    )

    column_names = ", ".join(quote_identifier(c) for c in columns)
    placeholders = ", ".join("?" for _ in columns)

    connection.executemany(
        f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})",
        [
            tuple(row.get(column, "") or "" for column in columns)
            for row in rows
        ],
    )

    print(f"LOADED: {table_name}: {len(rows):,} rows")


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        for table_name, csv_path in TABLES.items():
            load_csv(connection, table_name, csv_path)

    print("\nDatabase load complete.")
    print(f"Database location: {DB_PATH}")


if __name__ == "__main__":
    main()
