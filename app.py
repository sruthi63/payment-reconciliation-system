import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "payment_reconciliation.db"

st.set_page_config(
    page_title="Payment Reconciliation",
    page_icon="💳",
    layout="wide",
)

st.title("💳 Payment Reconciliation Dashboard")
st.caption("SQLite-powered payment monitoring and exception investigation")


def read_table(table_name):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn,
        )


if not DB_PATH.exists():
    st.error("Database not found. Run: python .\\src\\load_database.py")
    st.stop()

try:
    bank = read_table("bank_statement_lines")
    settlements = read_table("settlement_batches")
    matches = read_table("reconciliation_matches")
    exceptions = read_table("reconciliation_exceptions")
    duplicates = read_table("duplicate_settlement_lines")
    webhooks = read_table("duplicate_webhooks")
    refunds = read_table("refunds_before_capture")
except (sqlite3.Error, pd.errors.DatabaseError) as error:
    st.error(f"Could not read the database: {error}")
    st.stop()

# Overview metrics
st.subheader("1. Reconciliation overview")

bank_count = len(bank)
matched_count = len(matches)
match_rate = matched_count / bank_count * 100 if bank_count else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bank statement lines", f"{bank_count:,}")
c2.metric("Settlement batches", f"{len(settlements):,}")
c3.metric("Match report rows", f"{matched_count:,}")
c4.metric("Exception rows", f"{len(exceptions):,}")

c5, c6, c7 = st.columns(3)
c5.metric("Bank-line match rate", f"{match_rate:.2f}%")
c6.metric("Duplicate settlement rows", f"{len(duplicates):,}")
c7.metric("Refund anomaly alerts", f"{len(refunds):,}")

st.caption(
    "Match rate is match-report rows divided by bank statement lines. "
    "It is a row-based metric, not a monetary-value success rate."
)

st.divider()

# Charts
st.subheader("2. Reconciliation results")

if bank_count:
    chart_data = pd.DataFrame({
        "Category": ["Match report rows", "Bank lines not represented in matches"],
        "Count": [min(matched_count, bank_count), max(bank_count - matched_count, 0)],
    })
    st.bar_chart(chart_data.set_index("Category"))

st.subheader("3. Exception categories")

if exceptions.empty:
    st.info("No exception records found.")
else:
    possible_columns = [
        "exception_type",
        "issue_type",
        "reason",
        "exception_reason",
        "exception_category",
        "type",
        "status",
    ]
    column_lookup = {
        str(column).lower().replace(" ", "_"): column
        for column in exceptions.columns
    }
    category_column = next(
        (column_lookup[name] for name in possible_columns
         if name in column_lookup),
        None,
    )

    if category_column:
        counts = (
            exceptions[category_column]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Exception type")
            .reset_index(name="Count")
        )
        st.bar_chart(counts.set_index("Exception type"))
        st.dataframe(counts, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No standard exception-category column was identified. "
            "Use the report explorer below to inspect the available columns."
        )

st.divider()

# SQL-backed report explorer
st.subheader("4. Search and investigate records")

reports = {
    "Bank statement lines": "bank_statement_lines",
    "Settlement batches": "settlement_batches",
    "Reconciliation matches": "reconciliation_matches",
    "Reconciliation exceptions": "reconciliation_exceptions",
    "Duplicate settlement lines": "duplicate_settlement_lines",
    "Duplicate webhook events": "duplicate_webhooks",
    "Refund-before-capture alerts": "refunds_before_capture",
    "Processor events": "processor_events",
    "Payment attempts": "payment_attempts",
    "Payment orders": "payment_orders",
}

selected_label = st.selectbox("Choose a database table", list(reports))
table_name = reports[selected_label]
data = read_table(table_name)

search_text = st.text_input(
    "Search records",
    placeholder="Enter an attempt ID, reference, status, or amount",
)

if search_text.strip():
    mask = data.astype(str).apply(
        lambda column: column.str.contains(
            search_text.strip(),
            case=False,
            regex=False,
            na=False,
        )
    ).any(axis=1)
    data = data[mask]

st.write(f"Records displayed: {len(data):,}")
st.dataframe(data, use_container_width=True, hide_index=True)

st.download_button(
    "Download displayed records as CSV",
    data=data.to_csv(index=False).encode("utf-8"),
    file_name=table_name + ".csv",
    mime="text/csv",
)

st.divider()
st.subheader("5. Database information")
st.write(f"Database file: `{DB_PATH}`")
st.write("Data source: SQLite database")
st.caption(
    "To refresh the database after regenerating CSV data, run the "
    "reconciliation and detection scripts, then run src/load_database.py."
)
