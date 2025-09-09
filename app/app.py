from __future__ import annotations
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os, logging
from datetime import datetime
import streamlit as st
import pandas as pd

from app.utils.logging_conf import setup_logging
from app.models.schemas import REQUIRED_HEADERS, normalize_status_values, validate_headers
from app.components.kpis import render_kpis
from app.components.charts import render_course_chart
from app.services.graph_client import GraphClient
from app.services.data_store import InMemoryStore
from app.services.security import scan_csv_basic
from app.utils.session import get_state, set_state

setup_logging()
logger = logging.getLogger("app")

st.set_page_config(page_title="Compliance Dashboard (Offline)", layout="wide")

def require_auth() -> dict:
    return {"name": "Demo User", "email": "demo.user@example.com", "oid": "demo-oid"}

def get_store():
    return InMemoryStore()

def parse_uploaded_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    scan_csv_basic(df)
    validate_headers(df.columns.tolist())
    df.columns = [c.strip() for c in df.columns]
    df["Completion Status"] = df["Completion Status"].apply(normalize_status_values)
    if "Required Date" in df.columns:
        df["Required Date"] = pd.to_datetime(df["Required Date"], errors="coerce")
    return df

def render_sidebar(user):
    st.sidebar.header("Data Upload & Filters")
    uploaded_file = st.sidebar.file_uploader("Upload CSV (PII; validated)", type=["csv"])
    df = get_state("dataset")
    if uploaded_file is not None:
        try:
            df = parse_uploaded_csv(uploaded_file)
            set_state("dataset", df)
            st.sidebar.success(f"Loaded {len(df)} rows.")
        except Exception as ex:
            st.sidebar.error(f"CSV error: {ex}")
            logger.exception("CSV parse error")

    if df is not None and not df.empty:
        org = st.sidebar.multiselect("Org", sorted(df["Org"].dropna().unique().tolist()))
        bu = st.sidebar.multiselect("BU", sorted(df["BU"].dropna().unique().tolist()))
        dept = st.sidebar.multiselect("Department", sorted(df["Department"].dropna().unique().tolist()))
        course = st.sidebar.multiselect("Course", sorted(df["Course Title"].dropna().unique().tolist()))
        filters = {"Org": org, "BU": bu, "Department": dept, "Course Title": course}
        set_state("filters", filters)

    st.sidebar.divider()
    st.sidebar.subheader("Email Reminders (Simulated)")
    st.sidebar.caption("Offline mode: emails are simulated; nothing is sent.")
    if st.sidebar.button("Simulate reminders for incomplete"):
        set_state("reminder_action", {"ts": datetime.utcnow().isoformat()})

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filters = get_state("filters") or {}
    for col, selected in filters.items():
        if selected:
            df = df[df[col].isin(selected)]
    return df

def compute_and_send_reminders(user, df: pd.DataFrame):
    client = GraphClient()
    incomplete = df[df["Completion Status"] != "Completed"]
    if incomplete.empty:
        st.info("No incomplete items found.")
        return []

    by_user = incomplete.groupby("Email Address")
    results = []
    for learner_email, sub in by_user:
        learner_name = sub.iloc[0].get("Learner") or f"{sub.iloc[0].get('First Name','')} {sub.iloc[0].get('Last Name','')}".strip()
        manager_email = sub.iloc[0].get("Manager Email") or client.get_manager(learner_email)

        rows = "".join(f"<li>{r['Course Title']} (required: {str(r.get('Required Date','')).split(' ')[0]})</li>" for _, r in sub.iterrows())
        with open(os.path.join(os.path.dirname(__file__), "email_templates", "reminder.html"), "r", encoding="utf-8") as f:
            template = f.read()
        html = template.replace("{{LEARNER_NAME}}", learner_name or learner_email)                       .replace("{{LEARNER_EMAIL}}", learner_email)                       .replace("{{COURSE_LIST}}", rows)                       .replace("{{SENDER_NAME}}", user.get("name") or "Compliance Team")

        st.write(f"SIMULATED SEND → to: {learner_email}  cc: []  items: {int(sub.shape[0])}")
        msg_id = client.send_mail("me", [learner_email], [], "Action required: Mandatory learning pending", html)
        results.append({"email": learner_email, "status": "simulated", "id": msg_id, "cc": [], "course_count": int(sub.shape[0])})

    st.success(f"Simulation complete — {len(results)} recipients.")
    return results

def main():
    user = require_auth()
    st.sidebar.write(f"Signed in as **{user.get('name','')}** ({user.get('email','')})")

    render_sidebar(user)
    df = get_state("dataset")

    if df is None or df.empty:
        st.info("Upload a CSV to get started. Required headers: " + ", ".join(REQUIRED_HEADERS))
        return

    filtered = apply_filters(df)

    kpi_cols = st.columns(3)
    render_kpis(kpi_cols, filtered)
    st.divider()
    render_course_chart(filtered)

    st.subheader("Individual Lookup")
    q = st.text_input("Search by name or email")
    if q:
        ql = q.strip().lower()
        per = df[(df["Learner"].str.lower().str.contains(ql, na=False)) | (df["Email Address"].str.lower() == ql)]
        st.dataframe(per.sort_values(["Learner", "Course Title"]))

    action = get_state("reminder_action")
    if action and action.get("ts"):
        results = compute_and_send_reminders(user, filtered)
        store = get_store()
        store.log_reminder_batch(user.get("email"), results or [])

if __name__ == "__main__":
    main()
