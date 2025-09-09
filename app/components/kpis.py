from __future__ import annotations
import streamlit as st
import pandas as pd

def render_kpis(cols, df: pd.DataFrame):
    total = int(df.shape[0])
    completed = int((df['Completion Status'] == 'Completed').sum())
    rate = (completed / total * 100) if total else 0
    outstanding = total - completed

    with cols[0]:
        st.metric('Overall Completion', f'{rate:.1f}%')
    with cols[1]:
        st.metric('Completed', f'{completed:,}')
    with cols[2]:
        st.metric('Outstanding', f'{outstanding:,}')
