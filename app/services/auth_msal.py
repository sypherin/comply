from __future__ import annotations
import os
import streamlit as st
import msal

TENANT = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"
SCOPES = os.getenv("GRAPH_SCOPES", "User.Read Mail.Send").split()

def _get_cache():
    cache = st.session_state.get("token_cache")
    if not cache:
        cache = msal.SerializableTokenCache()
        st.session_state["token_cache"] = cache
    return cache

def ensure_sign_in():
    if st.session_state.get("user_principal"):
        return
    if os.getenv("APP_ENV","local") != "local":
        st.error("MSAL interactive sign-in is only enabled for local development.")
        st.stop()
    cache = _get_cache()
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if not result:
        if st.button("Sign in to Microsoft"):
            flow = app.initiate_device_flow(scopes=SCOPES)
            if "user_code" not in flow:
                st.error("Failed to create device flow.")
                st.stop()
            st.info(f"Go to **{flow['verification_uri']}** and enter code **{flow['user_code']}**")
            result = app.acquire_token_by_device_flow(flow)
    if result and "access_token" in result:
        account = app.get_accounts()[0]
        st.session_state["user_principal"] = {"name": account.get("username"), "email": account.get("username"), "oid": account.get("home_account_id","")}
    else:
        st.stop()

def get_access_token(scopes: list[str] | None = None) -> str:
    scopes = scopes or SCOPES
    cache = _get_cache()
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
    if not result:
        result = app.acquire_token_interactive(scopes=scopes)
    if "access_token" not in result:
        raise RuntimeError(f"Failed to obtain token: {result.get('error_description')}")
    return result["access_token"]
