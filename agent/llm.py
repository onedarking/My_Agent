"""LLM interaction wrapper - supports OpenAI, DeepSeek, Ollama"""

import json
import os
import httpx
from config import LLM_PROVIDER, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def _get_client():
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    return httpx.Client(base_url=LLM_BASE_URL, headers=headers, timeout=120.0)


def chat(messages, system_prompt=None, temperature=0.3, max_tokens=4096):
    """Simple LLM chat. Returns text response."""
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    client = _get_client()
    try:
        resp = client.post(
            "/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LLM Error] {str(e)}"


def extract_structured(text, schema_description):
    """Ask LLM to extract structured info from text."""
    prompt = f"""从以下内容中提取信息，严格按照JSON格式返回（只返回JSON，不要其他文字）。

要提取的字段说明：
{schema_description}

内容：
{text[:8000]}
"""
    result = chat([{"role": "user", "content": prompt}], temperature=0.1)
    # Try to parse JSON from response
    try:
        # Find JSON block
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"raw": result.strip()}


def ask_question(context, question):
    """QA over document/data context."""
    prompt = f"""你是Office Agent的数据分析助手。基于以下数据内容回答用户的问题。
请给出准确、简洁的回答。如果数据不足以回答，就如实说。

数据内容：
{context[:12000]}

问题：{question}
"""
    return chat([{"role": "user", "content": prompt}], temperature=0.2)
