"""Office Agent v2 - Settings: AI Model Configuration"""

import streamlit as st
import requests
import json

API_BASE = "http://127.0.0.1:8000"


def render():
    st.markdown("## ⚙️ AI 模型配置")
    st.markdown(
        "<div style='color:#8b8fa3; font-size:0.9rem; margin-bottom:1.5rem;'>"
        "配置 AI 提供商和 API Key，用于智能问答和文档提取功能"
        "</div>",
        unsafe_allow_html=True,
    )

    # Model presets
    presets = {
        "deepseek": {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-reasoner"],
            "default_model": "deepseek-chat",
            "docs_url": "https://platform.deepseek.com/api_keys",
            "note": "推荐，性价比高，速度快",
        },
        "openai": {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"],
            "default_model": "gpt-4o-mini",
            "docs_url": "https://platform.openai.com/api-keys",
            "note": "最成熟，但需要境外支付方式",
        },
        "siliconflow": {
            "name": "SiliconFlow (硅基流动)",
            "base_url": "https://api.siliconflow.cn/v1",
            "models": ["deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1", "Qwen/Qwen2.5-72B-Instruct", "Pro/deepseek-ai/DeepSeek-V3"],
            "default_model": "deepseek-ai/DeepSeek-V3",
            "docs_url": "https://cloud.siliconflow.cn",
            "note": "国内可用，免费额度多",
        },
        "ollama": {
            "name": "Ollama (本地)",
            "base_url": "http://localhost:11434/v1",
            "models": ["qwen2.5:7b", "qwen2.5:14b", "llama3.2:3b", "deepseek-r1:8b", "mistral:7b"],
            "default_model": "qwen2.5:7b",
            "docs_url": "",
            "note": "完全本地，无需联网，无需API Key",
        },
    }

    # ─── Provider selection ─────────────────────
    if "ai_provider" not in st.session_state:
        st.session_state.ai_provider = "deepseek"
    if "ai_api_key" not in st.session_state:
        st.session_state.ai_api_key = ""
    if "ai_base_url" not in st.session_state:
        st.session_state.ai_base_url = "https://api.deepseek.com/v1"
    if "ai_model" not in st.session_state:
        st.session_state.ai_model = "deepseek-chat"
    if "ai_connected" not in st.session_state:
        st.session_state.ai_connected = False

    # Provider card grid
    st.markdown("#### 选择 AI 提供商")
    cols = st.columns(4)

    provider_keys = list(presets.keys())
    for i, key in enumerate(provider_keys):
        p = presets[key]
        selected = st.session_state.ai_provider == key
        border = "2px solid #6c5ce7" if selected else "1px solid #2a2d3e"
        bg = "#1e2130" if selected else "#1a1d27"

        with cols[i]:
            st.markdown(
                f"""
                <div onclick="
                    var el = parent.document.querySelector('[data-provider=\"{key}\"]');
                    if(el) el.click();
                " style="
                    background:{bg}; border:{border}; border-radius:12px;
                    padding:1rem; text-align:center; cursor:pointer;
                    transition:all 0.2s; height:140px;
                    display:flex; flex-direction:column; justify-content:center;
                ">
                    <div style="font-size:2rem;">{p['name'][0]}</div>
                    <div style="color:#e8eaf0; font-weight:600; margin-top:0.3rem;">{p['name']}</div>
                    <div style="color:#5c6072; font-size:0.7rem; margin-top:0.2rem;">{p['note']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("选择", key=f"btn_{key}", use_container_width=True):
                st.session_state.ai_provider = key
                p = presets[key]
                st.session_state.ai_base_url = p["base_url"]
                st.session_state.ai_model = p["default_model"]
                st.session_state.ai_api_key = "" if key != "ollama" else "no-key-needed"
                st.session_state.ai_connected = False
                st.rerun()

    st.markdown("---")

    # ─── Configuration form ─────────────────────
    current_provider = presets.get(st.session_state.ai_provider, presets["deepseek"])

    col1, col2 = st.columns([3, 2])

    with col1:
        # API Base URL
        st.text_input(
            "API 地址",
            value=st.session_state.ai_base_url,
            key="input_base_url",
            help="OpenAI 兼容的 API 地址",
            on_change=lambda: setattr(st.session_state, "ai_base_url", st.session_state.input_base_url),
        )

        # API Key
        if st.session_state.ai_provider != "ollama":
            key_val = st.session_state.ai_api_key
            st.text_input(
                "API Key",
                value=key_val if key_val and key_val != "no-key-needed" else "",
                type="password",
                key="input_api_key",
                help=f"在此处获取: {current_provider['docs_url']}",
                placeholder="sk-...",
                on_change=lambda: setattr(st.session_state, "ai_api_key", st.session_state.input_api_key),
            )
        else:
            st.info("🔒 Ollama 本地运行，无需 API Key")

        # Model selection
        model_index = 0
        models_list = current_provider["models"]
        current_model = st.session_state.ai_model
        if current_model in models_list:
            model_index = models_list.index(current_model)

        st.selectbox(
            "模型",
            options=models_list,
            index=model_index,
            key="input_model",
            on_change=lambda: setattr(st.session_state, "ai_model", st.session_state.input_model),
        )

    with col2:
        st.markdown(f"##### ℹ️ {current_provider['name']}")
        st.markdown(
            f"""
            <div style="background:#1e2130; border:1px solid #2a2d3e; border-radius:12px; padding:1rem;">
                <div style="color:#8b8fa3; font-size:0.8rem;">
                    <p><strong>提供商:</strong> {current_provider['name']}</p>
                    <p><strong>推荐模型:</strong> {current_provider['default_model']}</p>
                    <p><strong>备注:</strong> {current_provider['note']}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if current_provider["docs_url"]:
            st.markdown(
                f"<a href='{current_provider['docs_url']}' target='_blank' style='color:#6c5ce7; font-size:0.8rem;'>获取 API Key →</a>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ─── Test & Apply ──────────────────────────
    col_a, col_b = st.columns([1, 3])

    with col_a:
        if st.button("🧪 测试连接", type="primary", use_container_width=True):
            with st.spinner("正在测试 AI 连接..."):
                try:
                    # Build the test request
                    api_key = st.session_state.ai_api_key
                    base_url = st.session_state.ai_base_url
                    model = st.session_state.ai_model

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}" if api_key and api_key != "no-key-needed" else "",
                    }

                    payload = {
                        "model": model,
                        "messages": [{"role": "user", "content": "回复OK即可"}],
                        "max_tokens": 10,
                    }

                    resp = requests.post(
                        f"{base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=15,
                    )

                    if resp.status_code == 200:
                        st.session_state.ai_connected = True
                        st.success("✅ 连接成功！AI 功能已可用")
                    else:
                        st.session_state.ai_connected = False
                        st.error(f"❌ 连接失败: HTTP {resp.status_code} - {resp.text[:200]}")

                except Exception as e:
                    st.session_state.ai_connected = False
                    st.error(f"❌ 连接失败: {str(e)[:200]}")

    with col_b:
        if st.button("💾 保存并应用到全局", use_container_width=True):
            # Save to session and write to a temp config marker
            from config import BASE_DIR
            marker = BASE_DIR / ".ai_config"
            config_data = {
                "provider": st.session_state.ai_provider,
                "api_key": st.session_state.ai_api_key,
                "base_url": st.session_state.ai_base_url,
                "model": st.session_state.ai_model,
            }
            with open(marker, "w") as f:
                json.dump(config_data, f)

            st.success(f"✅ 已保存！当前配置: {st.session_state.ai_provider} / {st.session_state.ai_model}")
            st.info("重启后端(uvicorn)后配置才会全局生效，但当前页面会话已可用")

    # ─── Connection status ─────────────────────
    st.markdown("---")

    status_icon = "🟢" if st.session_state.ai_connected else "🔴"
    status_text = "已连接" if st.session_state.ai_connected else "未连接"
    status_color = "#00cec9" if st.session_state.ai_connected else "#ff7675"

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; padding:0.8rem; 
                    background:#1e2130; border:1px solid #2a2d3e; border-radius:10px;">
            <span>{status_icon}</span>
            <span style="color:{status_color}; font-weight:600;">{status_text}</span>
            <span style="color:#5c6072; font-size:0.8rem;">
                {st.session_state.ai_provider} → {st.session_state.ai_model}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─── Custom provider ───────────────────────
    with st.expander("🔧 自定义提供商"):
        st.markdown("支持任何 OpenAI 兼容的 API 地址")
        st.text_input("自定义 API 地址", placeholder="https://your-api.com/v1", key="custom_url")
        st.text_input("自定义模型名", placeholder="your-model-name", key="custom_model")
        if st.button("应用自定义"):
            if st.session_state.custom_url and st.session_state.custom_model:
                st.session_state.ai_provider = "custom"
                st.session_state.ai_base_url = st.session_state.custom_url
                st.session_state.ai_model = st.session_state.custom_model
                st.rerun()
