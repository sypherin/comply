# Compliance Dashboard — OFFLINE EDITION (Rebuild)

This build is **100% offline**: no Microsoft Entra ID, Graph, Azure SQL, or any network calls.
It runs locally with a **demo user**, stores data **in-memory only**, and simulates email reminders.

## Quickstart
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py
```
