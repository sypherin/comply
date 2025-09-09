# app/app.py
from __future__ import annotations

# --- import path shim ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ------------------------

import os
import logging
from datetime import datetime
import streamlit as st
import pandas as pd

from app.utils.logging_conf import setup_logging
from app.models.schemas import REQUIRED_HEADERS, normalize_status_values, validate_headers
from app.components.kpis import render_kpis
from app.components.charts import render_course_chart
from app.services.auth_easy_auth import get_user_from_easy_auth
from app.services.graph_client import GraphClient
from app.services.data_store import InMemoryStore, SqlStore, get_sql_engine
from app.services.security import scan_csv_basic
from app.utils.session import get_state, set_state

setup_logging()
logger = logging.getLogger("app")

# ====== OFFLINE HARD DEFAULTS ======
OFFLINE_MODE = True if os.getenv("OFFLINE_MODE", "").lower() in ("1", "true", "yes") else True  # force True
AUTH_MODE = (os.getenv("AUTH_MODE") or "demo").lower()  # demo | msal | easy_auth
if OFFLINE_MODE:
    AUTH_MODE = "demo"  # force demo when offline
# ===================================

ALLOWED_EMAIL_DOMAINS = [d.strip().lower() for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()]
USE_AZURE_SQL = False  # force in-memory for offline/demo
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "90"))

# Import MSAL helpers **only if** we’re truly in msal mode and not offline
if AUTH_MODE == "msal" and not OFFLINE_MODE:
    from app.services.auth_msal import ensure_sign_in, get_access_token  # type: ignore
else:
    # Safe no-op shims to ensure we never hit MSAL
    def ensure_sign_in():  # type: ignore
        return None
    def get_access_token(scopes=None):  # type: ignore
        raise RuntimeError("MSAL is disabled in demo/offline mode.")

st.set_page_config(page_title="Compliance Dashboard", layout="wide")

def require_auth() -> dict:
    """Return user principal dict with name, email, oid. Never touches cloud in demo/offline."""
    if AUTH_MODE == "demo" or OFFLINE_MODE:
        return {"name": "Demo User", "email": "demo.user@example.com", "oid": "demo-oid"}

    if AUTH_MODE == "easy_auth":
        user = get_user_from_easy_auth(st.session_state.get("request_headers", {}))
    elif AUTH_MODE == "msal":
        ensure_sign_in()
        _ = get_access_token(["User.Read"])
        user = st.session_state.get("user_principal", {})
    else:
        user = {"name": "Demo User", "email": "demo.user@example.com", "oid": "demo-oid"}

    if not user:
        st.stop()

    email = (user.get("email") or "").lower()
    if ALLOWED_EMAIL_DOMAINS and not any(
        email.endswith("@" + d) or email.split("@")[-1] == d for d in ALLOWED_EMAIL_DOMAINS
    ):
        st.error("Your email domain is not allowed to access this application.")
        st.stop()
    return user

def get_store():
    if USE_AZURE_SQL and not OFFLINE_MODE and AUTH_MODE != "demo":
        engine = get_sql_engine()
        return SqlStore(engine=engine, retention_days=RETENTION_DAYS)
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
    st.sidebar.subheader("Email Reminders")
    cc_managers = st.sidebar.checkbox("CC Managers", value=False, disabled=True)
    dry_run = st.sidebar.checkbox("Dry Run (no send)", value=True)
    st.sidebar.caption("Demo/offline mode: emails are simulated; nothing will be sent.")
    if st.sidebar.button("Send reminders for incomplete"):
        set_state("reminder_action", {"cc_managers": cc_managers, "dry_run": dry_run, "ts": datetime.utcnow().isoformat()})

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filters = get_state("filters") or {}
    for col, selected in filters.items():
        if selected:
            df = df[df[col].isin(selected)]
    return df

def compute_and_send_reminders(user, df: pd.DataFrame):
    client = GraphClient()  # is a no-op in offline mode (see its own stub)
    incomplete = df[df["Completion Status"] != "Completed"]
    if incomplete.empty:
        st.info("No incomplete items found.")
        return

    by_user = incomplete.groupby("Email Address")
    results = []
    for learner_email, sub in by_user:
        learner_name = sub.iloc[0].get("Learner") or f"{sub.iloc[0].get('First Name','')} {sub.iloc[0].get('Last Name','')}".strip()
        manager_email = None  # disabled in demo

        rows = "".join(f"<li>{r['Course Title']} (required: {str(r.get('Required Date','')).split(' ')[0]})</li>" for _, r in sub.iterrows())
        with open(os.path.join(os.path.dirname(__file__), "email_templates", "reminder.html"), "r", encoding="utf-8") as f:
            template = f.read()
        html = template.replace("{{LEARNER_NAME}}", learner_name or learner_email)\
                       .replace("{{LEARNER_EMAIL}}", learner_email)\
                       .replace("{{COURSE_LIST}}", rows)\
                       .replace("{{SENDER_NAME}}", user.get("name") or "Compliance Team")

        cc = []
        st.write(f"DRY RUN: would send to {learner_email} cc {cc}")
        results.append({"email": learner_email, "status": "dry-run", "cc": cc, "course_count": int(sub.shape[0])})

    st.success(f"Reminder processing complete — {len(results)} targeted.")
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

    # No SQL save in offline/demo

    action = get_state("reminder_action")
    if action and action.get("ts"):
        results = compute_and_send_reminders(user, filtered)
        store = get_store()
        store.log_reminder_batch(user.get("email"), results or [])

if __name__ == "__main__":
    main()
