"""Office Agent v2 - Agent Execution Flow (form-based, bulletproof)"""

import streamlit as st
import requests
from datetime import datetime

API_BASE = "http://127.0.0.1:8000"


def _file_list():
    try:
        r = requests.get(f"{API_BASE}/api/files?dir=raw", timeout=3)
        return [f["name"] for f in r.json().get("files", [])]
    except:
        return []


def render():
    st.markdown("## 🤖 Agent 执行流程")

    wf_options = {
        "pdf_to_word": "📄 PDF → Word 转换",
        "pdf_to_excel": "📊 PDF → Excel 提取",
        "excel_clean": "🧹 Excel 数据清洗",
        "batch": "📁 批量改名 + 归档",
    }

    # Upload area
    uploaded = st.file_uploader("📤 上传文件", type=["pdf", "xlsx", "xls", "csv", "docx", "txt"], key="wf_upload")
    if uploaded is not None:
        # Use session state to prevent re-upload on rerun
        if "last_uploaded" not in st.session_state or st.session_state.last_uploaded != uploaded.name:
            st.session_state.last_uploaded = uploaded.name
            try:
                r = requests.post(
                    f"{API_BASE}/api/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                    timeout=30,
                )
                if r.status_code == 200:
                    st.success(f"✅ {uploaded.name} 上传成功")
                    st.rerun()
                else:
                    st.error(f"上传失败: {r.text[:100]}")
            except Exception as e:
                st.error(f"❌ 无法连接后端: {e}")
    files = _file_list()

    if not files:
        st.info("📭 还没有文件，请先上传")
        st.markdown("---")
        st.markdown("#### 📋 执行历史")
        _show_logs()
        return

    with st.form("wf_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            wf = st.selectbox("选择工作流", list(wf_options.keys()), format_func=lambda x: wf_options[x])

        # 右侧：有文件显示选择器，无文件显示提示
        if files:
            fname = st.selectbox("选择文件", files, key="wf_file_selector")
        else:
            fname = None
            st.markdown("<div style='color:#5c6072; padding-top:1.5rem;'>请先上传文件</div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("🚀 执行工作流", type="primary", width="stretch", disabled=(not files))

    # ─── Add inline override for form submit buttons ─────
    st.markdown("""
    <style>
    button[data-testid="stFormSubmitButton"] {
        color: white !important;
        font-weight: 700 !important;
    }
    button[data-testid="stFormSubmitButton"]:hover {
        color: white !important;
    }
    button[data-testid="baseButton-primary"] {
        color: white !important;
    }
    button[data-testid="baseButton-primary"]:hover {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ─── Process outside form ─────
    if submitted:
        if not fname:
            st.warning("⚠️ 请先上传文件后执行")
            st.markdown("---")
            _show_logs()
            return
        st.markdown("---")
        st.markdown("#### 📊 执行结果")

        with st.spinner("🤖 Agent 正在执行工作流..."):
            try:
                r = requests.post(
                    f"{API_BASE}/api/workflow/run",
                    json={"workflow": wf, "file": fname},
                    timeout=120,
                )
            except Exception as e:
                st.error(f"❌ 连接后端失败: {e}")
                st.markdown("---")
                _show_logs()
                return

        if r.status_code != 200:
            st.error(f"❌ API 错误 ({r.status_code}): {r.text[:300]}")
            st.markdown("---")
            _show_logs()
            return

        data = r.json()
        steps = data.get("steps", [])

        if not steps:
            st.warning("无步骤数据")
        else:
            success = sum(1 for s in steps if s["status"] == "success")
            total = len(steps)
            all_ok = success == total
            pct = success / total

            # ── Progress bar ──
            st.markdown(f"""
            <div style="margin:1rem 0;">
                <div style="display:flex;justify-content:space-between;color:#8b8fa3;font-size:0.8rem;">
                    <span>进度</span><span>{success}/{total}</span>
                </div>
                <div style="background:#1a1d27;border-radius:10px;height:10px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#6c5ce7,#00cec9);width:{pct*100}%;height:100%;border-radius:10px;transition:width 0.5s;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Summary ──
            color = "#00cec9" if all_ok else "#ff7675"
            st.markdown(f"""
            <div style="text-align:center;padding:0.7rem;border-radius:10px;margin-bottom:1rem;
                        background:{color}15;border:1px solid {color};">
                <span style="font-size:1.2rem;">{"🎉" if all_ok else "⚠️"}</span>
                <span style="color:{color};font-weight:600;font-size:1rem;margin-left:0.3rem;">
                    {"全部完成！" if all_ok else f"{total-success} 个步骤失败"}
                </span>
                <span style="color:#8b8fa3;font-size:0.85rem;margin-left:0.5rem;">{success}/{total}</span>
            </div>
            """, unsafe_allow_html=True)

            # ── Step cards ──
            colors = {"success": "#00cec9", "failed": "#ff7675", "pending": "#5c6072", "running": "#74b9ff", "skipped": "#636e72"}
            icons = {"success": "✅", "failed": "❌", "pending": "⏳", "running": "🔄", "skipped": "⏭️"}

            for i, step in enumerate(steps):
                s = step["status"]
                c = colors.get(s, "#5c6072")
                ic = icons.get(s, "❓")

                elapsed = ""
                if step.get("started_at") and step.get("ended_at"):
                    try:
                        sdt = datetime.fromisoformat(step["started_at"])
                        edt = datetime.fromisoformat(step["ended_at"])
                        elapsed = f"{(edt-sdt).total_seconds():.1f}s"
                    except:
                        pass

                # Parse output path
                out_path = ""
                result_str = str(step.get("result", ""))
                if result_str and s == "success":
                    for q in ["'", '"']:
                        m = f"{q}output{q}: {q}"
                        if m in result_str:
                            start = result_str.find(m) + len(m)
                            end = result_str.find(q, start)
                            if end > start:
                                out_path = result_str[start:end]
                                break

                err_text = str(step.get("error", ""))[:150] if step.get("error") else ""

                st.markdown(f"""
                <div style="background:#1e2130;border:1px solid #2a2d3e;border-left:4px solid {c};
                            border-radius:10px;padding:1rem 1.2rem;margin:0.5rem 0;">
                    <div style="display:flex;align-items:center;gap:0.8rem;">
                        <div style="font-size:1.3rem;min-width:1.8rem;text-align:center;">{ic}</div>
                        <div style="flex:1">
                            <div style="color:#e8eaf0;font-weight:600;font-size:0.9rem;">#{i+1} {step['name']}</div>
                            <div style="color:#8b8fa3;font-size:0.78rem;">{step['description']}</div>
                        </div>
                        <div style="text-align:right;">
                            <span style="background:{c}20;color:{c};border:1px solid {c}40;
                                border-radius:20px;padding:0.15rem 0.7rem;font-size:0.7rem;font-weight:500;white-space:nowrap;">
                                {s.upper()}
                            </span>
                            {f'<div style="color:#5c6072;font-size:0.65rem;margin-top:0.2rem;">{elapsed}</div>' if elapsed else ''}
                        </div>
                    </div>
                    {f'<div style="color:#00cec9;font-size:0.78rem;margin-top:0.4rem;padding-top:0.4rem;border-top:1px solid #2a2d3e;word-break:break-all;">📁 {out_path}</div>' if out_path else ''}
                    {f'<div style="color:#ff7675;font-size:0.78rem;margin-top:0.4rem;">❌ {err_text}</div>' if err_text else ''}
                </div>
                """, unsafe_allow_html=True)

                if i < len(steps) - 1:
                    st.markdown("""<div style="text-align:center;color:#2a2d3e;font-size:0.7rem;padding:0.1rem 0;">⬇</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📋 执行历史")
    _show_logs()


def _show_logs():
    try:
        logs = requests.get(f"{API_BASE}/api/logs", params={"limit": 15}, timeout=3).json().get("logs", [])
        for log in reversed(logs[-15:]):
            ts = log.get("timestamp", "")
            action = log.get("action", "")
            file = log.get("file", "")
            s = log.get("status", "")
            icon = {"success": "✅", "failed": "❌", "processing": "⏳"}.get(s, "➡️")
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;"
                f"border-bottom:1px solid #1e2130;font-size:0.85rem;'>"
                f"<span style='color:#5c6072;font-size:0.75rem;min-width:4rem;'>{ts[11:19]}</span>"
                f"<span>{icon}</span>"
                f"<code style='color:#8b8fa3;font-size:0.78rem;'>{action}</code>"
                f"<span>{file}</span></div>",
                unsafe_allow_html=True,
            )
    except:
        st.warning("无法获取执行记录")
