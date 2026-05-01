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

    # Use radio instead of tabs to avoid Streamlit 1.57 ElementNode bug
    mode = st.radio(
        "模式",
        ["📋 工作流", "🧠 智能 Agent"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "📋 工作流":
        _render_workflow()
    else:
        _render_true_agent()


def _render_workflow():
    """Workflow tab with simple conditional rendering."""

    wf_options = {
        "pdf_to_word": "📄 PDF → Word 转换",
        "pdf_to_excel": "📊 PDF → Excel 提取",
        "excel_clean": "🧹 Excel 数据清洗",
        "batch": "📁 批量改名 + 归档",
    }

    # Upload area
    uploaded = st.file_uploader("📤 上传文件", type=["pdf", "xlsx", "xls", "csv", "docx", "txt"], key="wf_upload")
    uploaded_name = None
    if uploaded is not None:
        uploaded_name = uploaded.name
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

    if not files and not uploaded:
        st.info("📭 还没有文件，请先上传")
        st.markdown("---")
        st.markdown("#### 📋 执行历史")
        _show_logs()
        return

    if files:
        col1, col2 = st.columns(2)
        with col1:
            wf = st.selectbox("选择工作流", list(wf_options.keys()), format_func=lambda x: wf_options[x], key="wf_select_workflow")
        with col2:
            fname = st.selectbox("选择文件", files, key="wf_select_file")

        if st.button("🚀 执行工作流", type="primary", use_container_width=True, key="wf_execute_btn") and fname:
            _execute_workflow(wf, fname)
    else:
        # Files just appeared (after upload), will show on next rerun
        st.info("📭 文件列表为空，上传后请稍候...")

    st.markdown("---")
    st.markdown("#### 📋 执行历史")
    _show_logs()


def _execute_workflow(wf, fname):
    """Execute a workflow and display results."""
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


def _render_true_agent():
    """True Agent: user gives a goal, LLM plans and executes autonomously."""
    st.markdown("### 🧠 智能 Agent")
    st.markdown(
        "<div style='color:#8b8fa3; font-size:0.9rem; margin-bottom:1rem;'>"
        "给 Agent 一个模糊指令，它会自己决定用什么工具、按什么顺序执行。"
        "<br>例如：<code>帮我处理这批PDF文件</code> 或 <code>整理data目录下的所有文件</code>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Show available files
    try:
        files = requests.get(f"{API_BASE}/api/files?dir=raw", timeout=3).json().get("files", [])
        if files:
            st.markdown(
                f"<div style='color:#5c6072; font-size:0.8rem; margin-bottom:0.5rem;'>"
                f"当前有 {len(files)} 个文件可处理: {', '.join(f['name'] for f in files[:5])}"
                + ("..." if len(files) > 5 else "") + "</div>",
                unsafe_allow_html=True,
            )
    except:
        pass

    goal = st.text_area(
        "输入你的指令",
        placeholder="例如：把data/raw里的PDF都转成Word，然后整理归档",
        height=80,
        key="agent_goal",
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        run_btn = st.button("🚀 执行", type="primary", disabled=(not goal.strip()), key="agent_run_btn")
    with col2:
        st.markdown(
            "<div style='padding-top:0.3rem; color:#5c6072; font-size:0.8rem;'>"
            "Agent 会依次执行多个步骤，请耐心等待</div>",
            unsafe_allow_html=True,
        )

    if run_btn and goal.strip():
        result_area = st.empty()
        with result_area.container():
            with st.spinner("🧠 Agent 正在思考并执行..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/agent/think",
                        json={"goal": goal.strip()},
                        timeout=180,
                    )
                    result_area.empty()

                    if resp.status_code == 200:
                        data = resp.json()
                        thinking_log = data.get("thinking_log", "")
                        result = data.get("result", {})

                        st.success("✅ Agent 任务完成！")

                        # Show thinking log as a nice formatted report
                        st.markdown("#### 🧠 Agent 思考过程")
                        log_lines = thinking_log.split("\n")
                        for line in log_lines:
                            if line.strip():
                                st.markdown(f"<div style='font-size:0.85rem;'>{line}</div>", unsafe_allow_html=True)

                        # Show step summary
                        steps = result.get("steps", [])
                        if steps:
                            st.markdown("#### 📊 执行摘要")
                            done = sum(1 for s in steps if s.get("status") == "completed" or s.get("status") == "success")
                            st.markdown(
                                f"<div style='color:#8b8fa3; font-size:0.85rem;'>"
                                f"共 {len(steps)} 步，成功 {done} 步</div>",
                                unsafe_allow_html=True,
                            )

                        # Raw result expander
                        with st.expander("📄 原始执行数据"):
                            st.json(result)
                    else:
                        st.error(f"❌ Agent 执行失败: HTTP {resp.status_code}")
                        st.code(resp.text[:500])

                except requests.exceptions.ConnectionError:
                    result_area.empty()
                    st.error("❌ 无法连接后端 API，请确认 uvicorn 正在运行")
                except Exception as e:
                    result_area.empty()
                    st.error(f"❌ 执行出错: {str(e)[:300]}")
