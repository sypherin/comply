from __future__ import annotations
import streamlit as st

# OFFLINE stub: never talks to MSAL/Azure

def ensure_sign_in():
    """No-op sign-in for demo/offline mode."""
    st.session_state["user_principal"] = {
        "name": "Demo User",
        "email": "demo.user@example.com",
        "oid": "demo-oid",
    }

def get_access_token(scopes: list[str] | None = None) -> str:
    """Intentionally disabled offline."""
    raise RuntimeError("Access tokens are disabled in demo/offline mode.")
