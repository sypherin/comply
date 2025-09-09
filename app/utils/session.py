from __future__ import annotations
import streamlit as st

def get_state(key: str):
    return st.session_state.get(key)

def set_state(key: str, value):
    st.session_state[key] = value
