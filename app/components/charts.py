from __future__ import annotations
import streamlit as st
import plotly.express as px
import pandas as pd

def render_course_chart(df: pd.DataFrame):
    st.subheader("Per-course completion")
    if df.empty:
        st.info("No data to chart.")
        return
    grouped = df.groupby(["Course Title", "Completion Status"]).size().reset_index(name="count")
    try:
        fig = px.bar(grouped, x="Course Title", y="count", color="Completion Status", barmode="stack")
        fig.update_layout(xaxis_title="", yaxis_title="Learners", legend_title_text="Status", margin=dict(l=10, r=10, t=10, b=80))
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.warning("Could not render chart. Check data formatting.")
