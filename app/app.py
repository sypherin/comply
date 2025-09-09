from __future__ import annotations
import os
import logging
from datetime import datetime
import streamlit as st
import pandas as pd

# 🔁 absolute imports (fix for ImportError in Streamlit)
from app.utils.logging_conf import setup_logging
from app.models.schemas import REQUIRED_HEADERS, normalize_status_values, validate_headers
from app.components.kpis import render_kpis
from app.components.charts import render_course_chart
from app.services.auth_easy_auth import get_user_from_easy_auth
from app.services.auth_msal import ensure_sign_in, get_access_token
from app.services.graph_client import GraphClient
from app.services.data_store import InMemoryStore, SqlStore, get_sql_engine
from app.services.security import scan_csv_basic
from app.utils.session import get_state, set_state

setup_logging()
logger = logging.getLogger("app")

APP_ENV = os.getenv("APP_ENV", "local")
AUTH_MODE = os.getenv("AUTH_MODE", "msal")
ALLOWED_EMAIL_DOMAINS = [d.strip().lower() for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()]
USE_AZURE_SQL = os.getenv("USE_AZURE_SQL", "false").lower() == "true"
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "90"))

st.set_page_config(page_title="Compliance Dashboard", layout="wide")

def require_auth() -> dict:
    if AUTH_MODE == "easy_auth":
        user = get_user_from_easy_auth(st.session_state.get("request_headers", {}))
    else:
        ensure_sign_in()
        _ = get_access_token(["User.Read"])
        user = st.session_state.get("user_principal", {})
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
    if USE_AZURE_SQL:
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
    cc_managers = st.sidebar.checkbox("CC Managers", value=True)
    dry_run = st.sidebar.checkbox("Dry Run (no send)", value=True)
    if st.sidebar.button("Send reminders for incomplete"):
        set_state(
            "reminder_action",
            {"cc_managers": cc_managers, "dry_run": dry_run, "ts": datetime.utcnow().isoformat()},
        )

    if USE_AZURE_SQL:
        st.sidebar.divider()
        st.sidebar.subheader("Storage")
        save_toggle = st.sidebar.checkbox("Persist dataset to Azure SQL", value=False)
        set_state("save_dataset", save_toggle)
        st.sidebar.caption(f"Retention: rows older than {RETENTION_DAYS} days are purged.")

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filters = get_state("filters") or {}
    for col, selected in filters.items():
        if selected:
            df = df[df[col].isin(selected)]
    return df

def compute_and_send_reminders(user, df: pd.DataFrame):
    cfg_scopes = os.getenv("GRAPH_SCOPES", "User.Read Mail.Send Directory.Read.All")
    client = GraphClient()
    incomplete = df[df["Completion Status"] != "Completed"]
    if incomplete.empty:
        st.info("No inc
