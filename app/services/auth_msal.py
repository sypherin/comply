from __future__ import annotations
import os
import streamlit as st
import msal

OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"

def _read_config():
    tenant = os.getenv("AZURE_TENANT_ID", "").strip()
    client_id = os.getenv("AZURE_CLIENT_ID", "").strip()
    authority_tenant = tenant if tenant else "organizations"
    authority = f"https://login.microsoftonline.com/{authority_tenant}"
    scopes = os.getenv("GRAPH_SCOPES", "User.Read Mail.Send").split()
    return tenant, client_id, authority, scopes

def _get_cache():
    cache = st.session_state.get("token_cache")
    if not cache:
        cache = msal.SerializableTokenCache()
        st.session_state["token_cache"] = cache
    return cache

def ensure_sign_in():
    # offline: do nothing (auth handled in app.py)
    if OFFLINE_MODE:
        st.session_state["user_principal"] = {"name":"Demo User","email":"demo.user@example.com","oid":"demo-oid"}
        return
    if st.session_state.get("user_principal"):
        return
    if os.getenv("APP_ENV", "local") != "local":
        st.error("MSAL sign-in is for local dev. Use Easy Auth in Azure.")
        st.stop()

    tenant, client_id, authority, scopes = _read_config()
    if not client_id:
        st.error("Missing AZURE_CLIENT_ID for AUTH_MODE=msal.")
        st.stop()

    cache = _get_cache()
    app = msal.PublicClientApplication(client_id, authority=authority, token_cache=cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(scopes, account=accounts[0]) if accounts else None
    if not result:
        if st.button("Sign in to Microsoft"):
            flow = app.initiate_device_flow(scopes=scopes)
            if "user_code" not in flow:
                st.error(f"Device flow failed. Check AZURE_TENANT_ID / network. Details: {flow}")
                st.stop()
            st.info(f"Go to **{flow['verification_uri']}** and enter code **{flow['user_code']}**")
            result = app.acquire_token_by_device_flow(flow)
    if result and "access_token" in result:
        account = app.get_accounts()[0]
        st.session_state["user_principal"] = {
            "name": account.get("username"),
            "email": account.get("username"),
            "oid": account.get("home_account_id", ""),
        }
    else:
        err = (result or {}).get("error_description", "No token result. Check configuration.")
        st.error(f"MSAL sign-in failed. {err}")
        st.stop()

def get_access_token(scopes: list[str] | None = None) -> str:
    if OFFLINE_MODE:
        raise RuntimeError("OFFLINE_MODE=true: no access tokens available.")
    _, client_id, authority, default_scopes = _read_config()
    if os.getenv("APP_ENV", "local") != "local":
        raise RuntimeError("get_ac_
