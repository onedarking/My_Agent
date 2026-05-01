"""Office Agent v2 - Dashboard"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from pathlib import Path

API_BASE = "http://127.0.0.1:8000"


def render():
    st.markdown("## 📊 仪表盘")

    # Stats row
    try:
        dash = requests.get(f"{API_BASE}/api/dashboard", timeout=5).json()
    except:
        st.error("⚠️ API 服务未启动，请先运行后端：`uvicorn main:app --reload`")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📁 原始文件", dash.get("raw_files", 0))
    with col2:
        st.metric("📦 已处理", dash.get("processed_files", 0))
    with col3:
        st.metric("📝 操作日志", dash.get("log_entries", 0))
    with col4:
        st.metric("🔧 引擎状态", "✅ 运行中")

    st.markdown("---")

    # Two-column layout
    left, right = st.columns([3, 2])

    with left:
        st.markdown("### 📂 文件类型分布")
        file_types = dash.get("file_types", {})
        if file_types:
            df_types = pd.DataFrame([
                {"类型": ext if ext else "其他", "数量": count}
                for ext, count in sorted(file_types.items(), key=lambda x: -x[1])
            ])
            fig = px.bar(
                df_types, x="类型", y="数量",
                color="数量", color_continuous_scale=["#6c5ce7", "#a29bfe", "#00cec9"],
                text_auto=True, height=300,
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#8b8fa3",
                margin=dict(l=0, r=0, t=0, b=0),
            )
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📭 暂无文件，请先上传")

    with right:
        st.markdown("### 🕐 最近操作")
        try:
            logs = requests.get(f"{API_BASE}/api/logs", params={"limit": 8}, timeout=3).json().get("logs", [])
            if logs:
                for log in reversed(logs[-8:]):
                    status_icon = {"success": "✅", "failed": "❌", "processing": "⏳"}.get(log.get("status", ""), "➡️")
                    st.markdown(
                        f"<div style='padding:0.4rem 0; border-bottom:1px solid #2a2d3e; font-size:0.85rem'>"
                        f"{status_icon} <code>{log.get('action','')}</code> "
                        f"<span style='color:#8b8fa3'>{log.get('file','')}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("暂无操作记录")
        except:
            st.warning("无法获取日志")

    st.markdown("---")

    # Quick actions - use session state to navigate
    if "nav_target" not in st.session_state:
        st.session_state.nav_target = None

    st.markdown("### 🚀 快速操作")
    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    with qcol1:
        if st.button("📄 PDF → Word", use_container_width=True):
            st.session_state.nav_target = "agent"
            st.rerun()
    with qcol2:
        if st.button("📊 PDF → Excel", use_container_width=True):
            st.session_state.nav_target = "agent"
            st.rerun()
    with qcol3:
        if st.button("🧹 数据清洗", use_container_width=True):
            st.session_state.nav_target = "agent"
            st.rerun()
    with qcol4:
        if st.button("📁 归档整理", use_container_width=True):
            st.session_state.nav_target = "agent"
            st.rerun()
