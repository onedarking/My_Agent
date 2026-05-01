"""Office Agent v2 - Deep Analysis + AI Chat"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np
from pathlib import Path
from config import PROCESSED_DIR, RAW_DIR

API_BASE = "http://127.0.0.1:8000"


def render():
    st.markdown("## 🔬 深度分析 & AI 对话")
    st.markdown(
        "<div style='color:#8b8fa3; font-size:0.9rem; margin-bottom:1.5rem;'>"
        "对数据做多维度统计分析，或直接向 AI 询问数据问题"
        "</div>",
        unsafe_allow_html=True,
    )

    tab_analysis, tab_stats, tab_ai = st.tabs(["📈 数据分析", "📊 统计报告", "💬 AI 问答"])

    # ─── Tab 1: Data Analysis ──────────────────────
    with tab_analysis:
        _render_data_preview()

    # ─── Tab 2: Statistics Report ──────────────────
    with tab_stats:
        _render_stats_report()

    # ─── Tab 3: AI Chat ────────────────────────────
    with tab_ai:
        _render_ai_chat()


def _get_dataframe(selected_file=None):
    """Get a DataFrame from the selected file. Returns (df, filename)."""
    try:
        raw_resp = requests.get(f"{API_BASE}/api/files", params={"dir": "raw"}, timeout=3).json().get("files", [])
        proc_resp = requests.get(f"{API_BASE}/api/files", params={"dir": "processed"}, timeout=3).json().get("files", [])
    except:
        return None, None

    all_files = [
        ("raw", f) for f in raw_resp
    ] + [
        ("processed", f) for f in proc_resp
    ]
    excel_files = [(d, f) for d, f in all_files if f["ext"] in (".xlsx", ".xls", ".csv")]

    if not excel_files:
        return None, None

    if not selected_file:
        selected_file = excel_files[0][1]["name"]

    # Find it
    for d, f in excel_files:
        if f["name"] == selected_file:
            base = RAW_DIR if d == "raw" else PROCESSED_DIR
            disk_path = base / selected_file
            if disk_path.exists():
                try:
                    df = pd.read_excel(str(disk_path)) if selected_file.endswith(('.xlsx', '.xls')) else pd.read_csv(str(disk_path), engine='python')
                    return df, selected_file
                except:
                    pass

    # Fallback: try all
    for d, f in excel_files:
        base = RAW_DIR if d == "raw" else PROCESSED_DIR
        disk_path = base / f["name"]
        if disk_path.exists():
            try:
                df = pd.read_excel(str(disk_path)) if f["name"].endswith(('.xlsx', '.xls')) else pd.read_csv(str(disk_path), engine='python')
                return df, f["name"]
            except:
                continue

    return None, None


def _get_file_list():
    """Get list of available excel/csv files."""
    try:
        raw = requests.get(f"{API_BASE}/api/files", params={"dir": "raw"}, timeout=3).json().get("files", [])
        proc = requests.get(f"{API_BASE}/api/files", params={"dir": "processed"}, timeout=3).json().get("files", [])
    except:
        raw, proc = [], []

    excel_ext = (".xlsx", ".xls", ".csv")
    names = []
    for f in raw:
        if f["ext"] in excel_ext:
            names.append(f["name"])
    for f in proc:
        if f["ext"] in excel_ext and f["name"] not in names:
            names.append(f["name"])
    return names


def _render_data_preview():
    """Original data analysis tab - enhanced."""
    file_names = _get_file_list()
    if not file_names:
        st.info("📭 没有找到表格文件(.xlsx/.xls/.csv)。先在 Agent 流程上传或处理文件。")
        return

    selected = st.selectbox("选择分析文件", file_names, key="analysis_file")
    df, _ = _get_dataframe(selected)
    if df is None:
        st.error("无法读取文件")
        return

    st.markdown("#### 📋 数据预览")
    st.dataframe(df.head(20), use_container_width=True, height=350)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("行数", df.shape[0])
    with col2:
        st.metric("列数", df.shape[1])
    with col3:
        st.metric("缺失值总数", int(df.isna().sum().sum()))
    with col4:
        st.metric("缺失率", f"{df.isna().sum().sum() / (df.shape[0]*df.shape[1]) * 100:.1f}%")

    # ── Missing value heatmap ──
    if df.isna().sum().sum() > 0:
        st.markdown("#### ⬜ 缺失值分布")
        missing_df = pd.DataFrame({
            "列名": df.columns,
            "缺失数": df.isna().sum().values,
            "缺失率(%)": (df.isna().sum().values / df.shape[0] * 100).round(1),
        }).sort_values("缺失数", ascending=False)

        fig_miss = px.imshow(
            df.isna().astype(int).T,
            labels={"x": "行索引", "y": "列", "color": "缺失"},
            color_continuous_scale=["#1a1d27", "#ff7675"],
            aspect="auto",
            height=max(200, 30 * df.shape[1]),
        )
        fig_miss.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#8b8fa3",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        fig_miss.update_xaxes(showticklabels=False)
        fig_miss.update_yaxes(tickfont_size=10)
        st.plotly_chart(fig_miss, use_container_width=True)

        with st.expander("📋 缺失详情"):
            st.dataframe(missing_df, use_container_width=True, hide_index=True)

    # ── Numeric columns ──
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        st.markdown("#### 📊 数值列分布")
        selected_cols = st.multiselect(
            "选择列查看分布", num_cols,
            default=num_cols[:min(4, len(num_cols))],
            key="dist_cols"
        )
        if selected_cols:
            fig = go.Figure()
            for i, col in enumerate(selected_cols):
                colors = ["#6c5ce7", "#00cec9", "#fdcb6e", "#ff7675", "#74b9ff", "#fd79a8"]
                fig.add_trace(go.Box(
                    y=df[col].dropna(), name=col,
                    marker_color=colors[i % len(colors)],
                    boxmean="sd",
                ))
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#8b8fa3", height=400,
                margin=dict(l=40, r=20, t=10, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Text columns ──
    text_cols = df.select_dtypes(include="object").columns.tolist()
    if text_cols:
        st.markdown("#### 📝 文本列频次")
        cat_col = st.selectbox("选择分类列", text_cols, key="cat_col")
        if cat_col:
            vc = df[cat_col].value_counts().head(15).reset_index()
            vc.columns = [cat_col, "数量"]
            fig = px.bar(
                vc, x=cat_col, y="数量",
                color="数量",
                color_continuous_scale=["#6c5ce7", "#a29bfe", "#00cec9"],
                text_auto=True, height=350,
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#8b8fa3",
                margin=dict(l=0, r=0, t=0, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Outlier highlight in table ──
    if num_cols and len(num_cols) >= 1:
        st.markdown("#### ⚠️ 异常值检测（IQR法）")
        outlier_col = st.selectbox("选择检测异常的列", num_cols, key="outlier_col")
        if outlier_col:
            q1 = df[outlier_col].quantile(0.25)
            q3 = df[outlier_col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = df[(df[outlier_col] < lower) | (df[outlier_col] > upper)]
            if len(outliers) > 0:
                st.markdown(
                    f"<div style='color:#ff7675; font-size:0.9rem;'>发现了 {len(outliers)} 条异常值 "
                    f"(正常范围: {lower:.2f} ~ {upper:.2f})</div>",
                    unsafe_allow_html=True,
                )
                st.dataframe(outliers, use_container_width=True, height=200)
            else:
                st.success("✅ 未检测到异常值")


def _render_stats_report():
    """New tab: comprehensive statistical report."""
    file_names = _get_file_list()
    if not file_names:
        st.info("📭 没有表格文件，请先上传数据。")
        return

    selected = st.selectbox("选择文件生成统计报告", file_names, key="stats_file")
    df, _ = _get_dataframe(selected)
    if df is None:
        st.error("无法读取文件")
        return

    # ── 1. Basic Descriptives ──
    st.markdown("#### 📊 描述性统计")
    num_df = df.select_dtypes(include="number")
    if not num_df.empty:
        desc = num_df.describe().T
        desc["缺失率(%)"] = (num_df.isna().sum() / len(num_df) * 100).round(1)
        desc = desc.round(2)
        desc.index.name = "列名"
        st.dataframe(desc, use_container_width=True, height=min(400, 40 * (len(desc) + 1)))
    else:
        st.info("没有数值列")

    st.markdown("---")

    # ── 2. Correlation Matrix ──
    if num_df.shape[1] >= 2:
        st.markdown("#### 🔗 相关性矩阵")
        corr = num_df.corr(numeric_only=True)
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            aspect="auto",
            height=max(350, 50 * len(corr)),
            zmin=-1, zmax=1,
            labels={"color": "相关系数"},
        )
        fig_corr.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#8b8fa3",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_corr, use_container_width=True)

        # Strong correlations
        st.markdown("#### 💡 强相关发现")
        corr_pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) >= 0.5:
                    corr_pairs.append({
                        "变量1": corr.columns[i],
                        "变量2": corr.columns[j],
                        "相关系数": f"{val:.3f}",
                        "强度": "强正相关" if val > 0.7 else ("中等正相关" if val > 0.5 else "中等负相关" if val < -0.5 else "强负相关"),
                    })
        if corr_pairs:
            st.dataframe(pd.DataFrame(corr_pairs), use_container_width=True, hide_index=True)
        else:
            st.info("未发现强相关（|r| >= 0.5）的变量对")

    st.markdown("---")

    # ── 3. Column-by-column stats ──
    st.markdown("#### 📋 逐列分析报告")
    report_rows = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        n_miss = int(df[col].isna().sum())
        miss_pct = round(n_miss / len(df) * 100, 1)
        n_unique = int(df[col].nunique())
        row = {"列名": col, "类型": dtype, "非空数": len(df) - n_miss, "缺失率(%)": miss_pct, "唯一值": n_unique}

        if pd.api.types.is_numeric_dtype(df[col]):
            row.update({
                "均值": round(df[col].mean(), 2) if not df[col].isna().all() else "-",
                "标准差": round(df[col].std(), 2) if not df[col].isna().all() else "-",
                "最小值": round(df[col].min(), 2) if not df[col].isna().all() else "-",
                "25%": round(df[col].quantile(0.25), 2) if not df[col].isna().all() else "-",
                "50%": round(df[col].quantile(0.5), 2) if not df[col].isna().all() else "-",
                "75%": round(df[col].quantile(0.75), 2) if not df[col].isna().all() else "-",
                "最大值": round(df[col].max(), 2) if not df[col].isna().all() else "-",
            })
        report_rows.append(row)

    report_df = pd.DataFrame(report_rows)
    st.dataframe(report_df, use_container_width=True, hide_index=True, height=min(500, 35 * len(report_df)))


def _render_ai_chat():
    """AI chat tab with data context."""
    st.markdown("#### 💬 向 AI 询问你的数据")

    # Context picker
    all_files = []
    try:
        for d in ["raw", "processed"]:
            r = requests.get(f"{API_BASE}/api/files", params={"dir": d}, timeout=3).json().get("files", [])
            for f in r:
                if f["ext"] in (".xlsx", ".xls", ".csv", ".txt", ".md", ".pdf"):
                    all_files.append(f"{d}/{f['name']}")
    except:
        pass

    context_file = st.selectbox(
        "选择参考文件作为上下文（可选）",
        [""] + all_files,
        format_func=lambda x: x.split("/")[-1] if "/" in x else x or "无上下文",
        key="ai_context_file",
    )

    # Read context
    context_text = ""
    if context_file:
        dir_type, fname = context_file.split("/", 1)
        base = RAW_DIR if dir_type == "raw" else PROCESSED_DIR
        fpath = base / fname
        if fpath.exists():
            try:
                if fpath.suffix in (".xlsx", ".xls"):
                    cdf = pd.read_excel(str(fpath))
                    context_text = cdf.to_string(max_rows=100)
                elif fpath.suffix == ".csv":
                    cdf = pd.read_csv(str(fpath), engine='python')
                    context_text = cdf.to_string(max_rows=100)
                else:
                    context_text = fpath.read_text(encoding="utf-8", errors="ignore")[:8000]
                st.markdown(
                    f"<div style='color:#00cec9; font-size:0.8rem;'>已加载 {len(context_text)} 字符上下文</div>",
                    unsafe_allow_html=True,
                )
            except:
                context_text = f"[无法读取: {fpath}]"

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                f"<div style='text-align:right; margin:0.5rem 0;'>"
                f"<div style='display:inline-block; background:#6c5ce7; color:white; "
                f"border-radius:18px 18px 4px 18px; padding:0.5rem 1rem; max-width:80%; "
                f"font-size:0.9rem;'>{msg['content']}</div></div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='text-align:left; margin:0.5rem 0;'>"
                f"<div style='display:inline-block; background:#1e2130; color:#e8eaf0; "
                f"border:1px solid #2a2d3e; border-radius:18px 18px 18px 4px; "
                f"padding:0.5rem 1rem; max-width:80%; font-size:0.9rem;'>{msg['content']}</div></div>",
                unsafe_allow_html=True
            )

    user_question = st.chat_input("输入你的数据问题，如「哪一列缺失最多？」...")
    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.spinner("AI 思考中..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/ai/ask",
                    json={"question": user_question, "context": context_text},
                    timeout=30,
                )
                answer = resp.json().get("answer", "无响应") if resp.status_code == 200 else f"⚠️ API 错误: {resp.status_code}"
            except Exception as e:
                answer = f"⚠️ 连接失败: {e}"

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history and st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()
