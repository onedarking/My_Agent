"""Agent orchestrator - manages execution flow with step-by-step status"""

import time
import json
from datetime import datetime

from agent.tools import (
    pdf_to_word, pdf_to_excel, extract_report_info,
    clean_excel_data, batch_rename, organize_by_type,
    get_data_summary, get_logs
)
from agent.llm import chat, extract_structured, ask_question


class AgentStep:
    """Single step in an agent execution plan."""
    def __init__(self, step_id, name, description, tool_func, params, depends_on=None):
        self.step_id = step_id
        self.name = name
        self.description = description
        self.tool_func = tool_func
        self.params = params
        self.depends_on = depends_on or []
        self.status = "pending"  # pending | running | success | failed | skipped
        self.result = None
        self.error = None
        self.started_at = None
        self.ended_at = None

    def to_dict(self):
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "depends_on": self.depends_on,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


class AgentOrchestrator:
    """Runs a workflow of AgentSteps with DAG dependency resolution."""

    def __init__(self):
        self.steps = {}
        self.flow_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.status = "idle"

    def add_step(self, step: AgentStep):
        self.steps[step.step_id] = step

    def get_flow_state(self):
        return {
            "flow_id": self.flow_id,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps.values()],
        }

    def _get_ready_steps(self):
        """Get steps whose dependencies are all completed."""
        ready = []
        for s in self.steps.values():
            if s.status != "pending":
                continue
            deps_ok = all(
                self.steps[d].status == "success"
                for d in s.depends_on
            )
            if deps_ok:
                ready.append(s)
        return ready

    def run(self):
        """Execute all steps in dependency order."""
        self.status = "running"

        while True:
            ready = self._get_ready_steps()
            if not ready:
                break

            for step in ready:
                step.status = "running"
                step.started_at = datetime.now().isoformat()
                try:
                    # Handle between raw and processed files naturally
                    result = step.tool_func(**step.params)
                    step.result = result
                    step.status = "success" if result.get("status") != "failed" else "failed"
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                step.ended_at = datetime.now().isoformat()

        # Mark any remaining pending steps as skipped
        for s in self.steps.values():
            if s.status == "pending":
                s.status = "skipped"

        self.status = "completed"
        return self.get_flow_state()


# ─── Pre-built workflows ───────────────────────────────

def workflow_pdf_to_word(pdf_path: str) -> dict:
    """Simple single-step workflow."""
    orch = AgentOrchestrator()
    orch.add_step(AgentStep("convert", "PDF转Word", "将PDF转换为Word文档", pdf_to_word, {"pdf_path": pdf_path}))
    return orch.run()


def workflow_pdf_to_excel(pdf_path: str) -> dict:
    orch = AgentOrchestrator()
    orch.add_step(AgentStep("extract", "PDF提取表格", "从PDF中提取表格数据到Excel", pdf_to_excel, {"pdf_path": pdf_path}))
    return orch.run()


def workflow_clean_excel(excel_path: str) -> dict:
    orch = AgentOrchestrator()
    orch.add_step(AgentStep("clean", "数据清洗", "清洗Excel数据", clean_excel_data, {"excel_path": excel_path}))
    return orch.run()


def workflow_extract_report(pdf_path: str) -> dict:
    """Multi-step: extract text, then analyze with LLM."""
    orch = AgentOrchestrator()

    # This step just gets the text ready
    orch.add_step(AgentStep(
        "extract_text", "提取文本", "从PDF中提取文本内容",
        extract_report_info, {"pdf_path": pdf_path}
    ))

    # We'll handle the LLM step separately since it needs the first step's output
    return orch.run()


def workflow_batch_process(directory: str) -> dict:
    """Chain: batch rename -> organize by type."""
    orch = AgentOrchestrator()
    orch.add_step(AgentStep(
        "rename", "批量改名", "按规则批量重命名文件",
        batch_rename, {"directory": directory, "pattern": "*", "prefix": "doc_"}
    ))
    orch.add_step(AgentStep(
        "organize", "整理归档", "按文件类型整理到子目录",
        organize_by_type, {"directory": directory},
        depends_on=["rename"]
    ))
    return orch.run()


def workflow_ask_ai(question: str, data_context: str = "") -> str:
    """AI Q&A over data."""
    return ask_question(data_context, question)
