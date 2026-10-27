# Payment Reconciliation System

## Project Overview
A Python-based payment reconciliation system that compares bank statement records with settlement data, identifies mismatches, and detects suspicious payment-processing events.

## Features
- Generate sample payment and settlement data.
- Reconcile bank statement lines with settlement records.
- Identify reconciliation exceptions and mismatches.
- Detect duplicate settlement lines and webhooks.
- Flag refunds that occur before capture.
- Store data in an SQLite database.
- Explore results using a Streamlit dashboard.

## Technologies Used
- Python
- Pandas
- SQLite
- Streamlit
- Pytest

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Launch dashboard: `python -m streamlit run app.py`
3. Run tests: `python -m pytest -v`

## Learning Outcomes
Demonstrates data processing, SQL integration, automated testing, reconciliation logic, anomaly detection, and dashboard development.
