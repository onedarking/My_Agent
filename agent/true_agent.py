"""True Agent - LLM-driven autonomous task planning & execution"""

import json
import traceback
from datetime import datetime
from pathlib import Path

from agent.tools import (
    pdf_to_word, pdf_to_excel, extract_report_info,
    clean_excel_data, batch_rename, organize_by_type,
    get_data_summary, get_logs, log_action,
)
from agent.llm import chat
from config import RAW_DIR, PROCESSED_DIR, BASE_DIR

# Try to load user's AI config from settings
_AI_CONFIG_PATH = BASE_DIR / ".ai_config"
if _AI_CONFIG_PATH.exists():
    try:
        import json as _json
        with open(_AI_CONFIG_PATH) as _f:
            _cfg = _json.load(_f)
        # Only use if it has an API key
        if _cfg.get("api_key") and _cfg["api_key"] != "no-key-needed":
            import os as _os
            _os.environ["OA_API_KEY"] = _cfg["api_key"]
            _os.environ["OA_BASE_URL"] = _cfg.get("base_url", "https://api.deepseek.com/v1")
            _os.environ["OA_MODEL"] = _cfg.get("model", "deepseek-chat")
    except:
        pass


# ─── Tool registry ─────────────────────────────────────

TOOL_DESCRIPTIONS = [
    {
        "name": "pdf_to_word",
        "description": "将PDF文件转换为Word文档。适合合同、报告等文本型PDF。",
        "params": {"pdf_path": "PDF文件路径（在data/raw/下）"},
        "func": pdf_to_word,
    },
    {
        "name": "pdf_to_excel",
        "description": "从PDF中提取表格数据到Excel。适合有表格的PDF。",
        "params": {"pdf_path": "PDF文件路径"},
        "func": pdf_to_excel,
    },
    {
        "name": "extract_report_info",
        "description": "从PDF中提取文本内容，准备给LLM分析。",
        "params": {"pdf_path": "PDF文件路径"},
        "func": extract_report_info,
    },
    {
        "name": "clean_excel_data",
        "description": "清洗Excel/CSV数据：去重、填充缺失值、异常值检测。",
        "params": {"excel_path": "Excel或CSV文件路径"},
        "func": clean_excel_data,
    },
    {
        "name": "batch_rename",
        "description": "批量重命名目录中的文件，可指定前缀。",
        "params": {"directory": "目录路径", "pattern": "文件匹配模式(如 *.pdf)", "prefix": "新文件名前缀"},
        "func": batch_rename,
    },
    {
        "name": "organize_by_type",
        "description": "按文件类型（文档/表格/图片等）整理归档到子目录。",
        "params": {"directory": "目录路径"},
        "func": organize_by_type,
    },
    {
        "name": "get_data_summary",
        "description": "获取数据目录的概览：文件数量、类型分布等。",
        "params": {},
        "func": get_data_summary,
    },
    {
        "name": "list_raw_files",
        "description": "列出data/raw/目录下的所有文件。",
        "params": {},
        "func": lambda: {"files": [f.name for f in RAW_DIR.iterdir() if f.is_file()]},
    },
]

TOOL_REGISTRY = {t["name"]: t for t in TOOL_DESCRIPTIONS}


# ─── Agent session ─────────────────────────────────────

class TrueAgent:
    """
    A real Agent that:
    1. Receives a user goal in natural language
    2. LLM plans a sequence of tool calls
    3. Executes each step, passing results back to LLM
    4. LLM reflects & decides next steps or finishes
    5. Returns a final report
    """

    SYSTEM_PROMPT = """你是一个办公自动化Agent。你可以使用以下工具来完成任务。

可用工具：
{tools_str}

执行规则：
1. 分析用户的指令，拆解为合适的步骤
2. 每次只返回一个步骤的JSON，格式为：
   {{"tool": "工具名", "params": {{"参数名": "参数值"}}, "reasoning": "为什么这样做"}}
3. 执行完一步后，我会把结果返回给你
4. 根据结果决定下一步做什么，或返回：
   {{"done": true, "summary": "任务完成总结"}}
5. 重要：如果某步失败，尝试替代方案或如实报告
6. 所有文件路径必须是绝对路径或相对于当前工作目录

请开始分析用户的指令。只返回JSON，不要其他文字。"""

    def __init__(self, session_id=None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.history = []  # [{role, content}]
        self.steps = []
        self.status = "idle"
        self.tools_str = self._format_tools()

    def _format_tools(self):
        lines = []
        for t in TOOL_DESCRIPTIONS:
            params_str = ", ".join(f"{k}={v}" for k, v in t["params"].items())
            lines.append(f"- {t['name']}({params_str}): {t['description']}")
        return "\n".join(lines)

    def _list_raw_files_context(self):
        """Add current file context for LLM."""
        try:
            files = [f.name for f in RAW_DIR.iterdir() if f.is_file()]
            if files:
                return f"\n当前 data/raw/ 目录中的文件:\n" + "\n".join(f"  - {f}" for f in files)
            return "\n当前 data/raw/ 目录为空（没有文件）"
        except:
            return ""

    def _llm_call(self, messages, max_tokens=2000):
        """Call LLM and get response."""
        try:
            result = chat(messages, system_prompt=None, temperature=0.3, max_tokens=max_tokens)
            return result
        except Exception as e:
            return f'{{"tool": "report_error", "params": {{"error": "{str(e)}"}}}}'

    def _execute_tool(self, tool_name, params):
        """Execute a tool and return result."""
        log_action("agent_tool", tool_name, "running", str(params))

        if tool_name == "report_error":
            return {"status": "error", "message": params.get("error", "")}

        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            return {"status": "failed", "error": f"未知工具: {tool_name}"}

        # Resolve relative paths
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and ("data/raw" in v or "data/processed" in v):
                # Already a relative path, leave it
                resolved[k] = v
            else:
                resolved[k] = v

        try:
            result = tool["func"](**resolved)
            log_action("agent_tool", tool_name, "success", str(result)[:100])
            return result
        except Exception as e:
            log_action("agent_tool", tool_name, "failed", str(e))
            return {"status": "failed", "error": str(e), "traceback": traceback.format_exc()}

    def run(self, user_goal: str) -> dict:
        """Main entry: execute agent loop for a user goal."""
        self.status = "running"
        self.history.append({"role": "user", "content": user_goal})

        # Get available files context
        file_context = self._list_raw_files_context()

        # Initial planning prompt
        system_msg = self.SYSTEM_PROMPT.format(tools_str=self.tools_str)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"用户的指令: {user_goal}\n{file_context}"},
        ]

        max_iterations = 10
        step_count = 0

        while step_count < max_iterations:
            step_count += 1

            # LLM decides next action
            llm_response = self._llm_call(messages)

            step_entry = {
                "step": step_count,
                "llm_reasoning": llm_response,
                "status": "running",
            }
            self.steps.append(step_entry)

            try:
                # Parse JSON from LLM response
                decision = self._parse_json(llm_response)
            except:
                step_entry["status"] = "failed"
                step_entry["error"] = f"LLM返回格式错误: {llm_response[:300]}"
                break

            # Check if done
            if decision.get("done"):
                step_entry["status"] = "completed"
                step_entry["summary"] = decision.get("summary", "任务完成")
                self.status = "completed"
                return self.get_result()

            # Execute tool
            tool_name = decision.get("tool", "")
            params = decision.get("params", {})
            reasoning = decision.get("reasoning", "")

            step_entry["tool"] = tool_name
            step_entry["params"] = params
            step_entry["reasoning"] = reasoning

            result = self._execute_tool(tool_name, params)
            step_entry["result"] = result
            step_entry["status"] = "success" if result.get("status") != "failed" else "failed"

            # Feed result back to LLM
            result_str = self._format_result(result)
            messages.append({"role": "assistant", "content": llm_response})
            messages.append({
                "role": "user",
                "content": f"步骤 {step_count} 完成。工具: {tool_name}\n结果: {result_str}\n\n请决定下一步。如果任务已完成，返回 {{\"done\": true, \"summary\": \"...\"}}",
            })

        # If we exit the loop without done signal
        self.status = "completed"
        return self.get_result()

    def _parse_json(self, text):
        """Parse JSON from LLM response, handling markdown fences."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())

    def _format_result(self, result):
        """Format tool result for LLM consumption."""
        if isinstance(result, dict):
            # Pick relevant fields, limit size
            relevant = {}
            for k in ["status", "output", "rows", "error", "files", "original_rows",
                       "cleaned_rows", "duplicates_removed", "outlier_columns", "file_types"]:
                if k in result:
                    relevant[k] = result[k]
            return json.dumps(relevant, ensure_ascii=False)[:2000]
        return str(result)[:2000]

    def get_result(self):
        """Get full execution result."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "user_goal": self.history[0]["content"] if self.history else "",
            "steps": [
                {
                    "step": s["step"],
                    "tool": s.get("tool", ""),
                    "reasoning": s.get("reasoning", ""),
                    "params": s.get("params", {}),
                    "status": s["status"],
                    "result": str(s.get("result", ""))[:300] if s.get("result") else None,
                    "error": s.get("error", ""),
                    "summary": s.get("summary", ""),
                }
                for s in self.steps
            ],
            "total_steps": len(self.steps),
        }

    def get_thinking_log(self):
        """Get a readable thought process log."""
        lines = [f"🤖 Agent 会话: {self.session_id}", f"🎯 目标: {self.history[0]['content'] if self.history else ''}", ""]
        for s in self.steps:
            status_icon = {"completed": "✅", "success": "✅", "failed": "❌", "running": "🔄"}.get(s["status"], "⏳")
            reasoning = s.get("reasoning", "")
            tool = s.get("tool", "")
            result = s.get("result", {})
            summary = s.get("summary", "")

            lines.append(f"  {status_icon} 步骤 {s['step']}: {reasoning}")
            if tool:
                lines.append(f"     🛠 工具: {tool}")
            if isinstance(result, dict) and result.get("output"):
                lines.append(f"     📁 输出: {result['output']}")
            if summary:
                lines.append(f"     📝 {summary}")
            if s.get("error"):
                lines.append(f"     ❌ {s['error']}")
            lines.append("")
        return "\n".join(lines)
