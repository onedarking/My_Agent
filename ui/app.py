"""Office Agent v2 - Streamlit Main Entry Point"""

import streamlit as st
from pathlib import Path

# Page config must be first
st.set_page_config(
    page_title="Office Agent v2",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Inline button style override (forces white bold text on buttons)
st.markdown("""
<style>
button, .stButton > button, .stFormSubmitButton > button,
button[kind="primaryFormSubmit"], button[kind="primary"] {
    background: linear-gradient(135deg, #6c5ce7, #a29bfe) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border: none !important;
    text-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
}
button:hover, .stButton > button:hover, .stFormSubmitButton > button:hover,
button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover {
    background: linear-gradient(135deg, #7c6df7, #b2acfe) !important;
    color: #ffffff !important;
    text-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
}
button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #2a2d3e !important;
    color: #e8eaf0 !important;
}
button:disabled {
    background: #2a2d3e !important;
    color: #5c6072 !important;
}
</style>

<script>
// Force button styles on every DOM change
new MutationObserver(function() {
    document.querySelectorAll('button').forEach(function(b) {
        if (!b.classList.contains('_patched')) {
            b.classList.add('_patched');
            b.style.color = '#ffffff';
            b.style.fontWeight = '700';
            b.style.setProperty('color', '#ffffff', 'important');
        }
        b.addEventListener('mouseenter', function() {
            this.style.color = '#ffffff';
        });
        b.addEventListener('mouseleave', function() {
            this.style.color = '#ffffff';
        });
    });
}).observe(document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

# Import page modules
from ui.dashboard import render as render_dashboard
from ui.agent_flow import render as render_agent_flow
from ui.analysis import render as render_analysis
from ui.settings import render as render_settings

# ─── Sidebar ─────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:1rem 0;">
            <div style="font-size:2.5rem; margin-bottom:0.5rem;">🤖</div>
            <div style="font-size:1.2rem; font-weight:700; color:#e8eaf0; letter-spacing:-0.02em;">
                Office Agent
            </div>
            <div style="color:#5c6072; font-size:0.75rem;">v2.0 · AI-Powered</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Navigation
    nav_options = ["📊 仪表盘", "🤖 Agent 流程", "🔬 深度分析", "⚙️ 设置"]
    nav = st.radio(
        "导航",
        nav_options,
        label_visibility="collapsed",
        index=0,
    )

    st.markdown("---")

    # Quick info
    st.markdown("##### ℹ️ 系统信息")
    st.markdown(
        """
        <div style="font-size:0.8rem; color:#8b8fa3;">
            <div>引擎: FastAPI + Streamlit</div>
            <div>AI: DeepSeek / Ollama</div>
            <div>状态: <span style="color:#00cec9;">● 待运行</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#5c6072; font-size:0.7rem; padding:1rem 0;'>"
        "Made with ❤️ by Hermes Agent</div>",
        unsafe_allow_html=True,
    )

# ─── Page routing ────────────────────────────────────

# Handle nav from dashboard quick actions
if "nav_target" in st.session_state and st.session_state.nav_target:
    target = st.session_state.nav_target
    st.session_state.nav_target = None
    if target == "agent":
        nav = "🤖 Agent 流程"
    elif target == "settings":
        nav = "⚙️ 设置"

if nav == "📊 仪表盘":
    render_dashboard()
elif nav == "🤖 Agent 流程":
    render_agent_flow()
elif nav == "🔬 深度分析":
    render_analysis()
elif nav == "⚙️ 设置":
    render_settings()
