"""Office Agent v2 - FastAPI Backend"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import RAW_DIR, PROCESSED_DIR
from agent.tools import (
    pdf_to_word, pdf_to_excel, extract_report_info,
    clean_excel_data, batch_rename, organize_by_type,
    get_data_summary, get_logs, log_action
)
from agent.orchestrator import AgentOrchestrator, AgentStep
from agent.true_agent import TrueAgent
from agent.llm import chat, extract_structured, ask_question

app = FastAPI(title="Office Agent v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── File upload & management ───────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to raw directory."""
    dest = RAW_DIR / file.filename
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    log_action("upload", file.filename, "success", f"{len(content)} bytes")
    return {"status": "success", "file": file.filename, "size": len(content)}


@app.get("/api/files")
def list_files(dir: str = "raw"):
    """List files in raw or processed directory."""
    target = RAW_DIR if dir == "raw" else PROCESSED_DIR
    if not target.exists():
        return {"files": []}
    files = []
    for f in sorted(target.iterdir()):
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
                "ext": f.suffix.lower(),
            })
    return {"files": files, "directory": str(target)}


# ─── Processing endpoints ───────────────────────────────

class ProcessRequest(BaseModel):
    file: str
    action: str  # pdf_to_word, pdf_to_excel, extract_info, excel_clean


@app.post("/api/process")
def process_file(req: ProcessRequest):
    """Execute a single processing action."""
    file_path = RAW_DIR / req.file
    if not file_path.exists():
        raise HTTPException(404, f"File not found: {req.file}")

    actions = {
        "pdf_to_word": lambda: pdf_to_word(str(file_path)),
        "pdf_to_excel": lambda: pdf_to_excel(str(file_path)),
        "extract_info": lambda: extract_report_info(str(file_path)),
        "excel_clean": lambda: clean_excel_data(str(file_path)),
    }

    fn = actions.get(req.action)
    if not fn:
        raise HTTPException(400, f"Unknown action: {req.action}")

    return fn()


@app.post("/api/batch/rename")
def batch_rename_endpoint(directory: str = "raw", pattern: str = "*", prefix: str = "doc_"):
    target = RAW_DIR if directory == "raw" else PROCESSED_DIR
    return {"results": batch_rename(str(target), pattern, prefix)}


@app.post("/api/batch/organize")
def organize_endpoint(directory: str = "raw"):
    target = RAW_DIR if directory == "raw" else PROCESSED_DIR
    return organize_by_type(str(target))


# ─── AI / Chat ──────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    context: str = ""


@app.post("/api/ai/ask")
def ai_ask(req: AskRequest):
    """Ask AI a question about the data."""
    return {"answer": workflow_ask_ai(req.question, req.context)}


class ExtractRequest(BaseModel):
    text: str
    extract_schema: str


@app.post("/api/ai/extract")
def ai_extract(req: ExtractRequest):
    """Extract structured data using LLM."""
    return {"result": extract_structured(req.text, req.extract_schema)}


# ─── Workflow (Agent Flow) ─────────────────────────────

class WorkflowRequest(BaseModel):
    workflow: str  # pdf_to_word, pdf_to_excel, excel_clean, batch
    file: str
    extra: str = ""


@app.post("/api/workflow/run")
def run_workflow(req: WorkflowRequest):
    """Run a full agent workflow with step tracking."""
    file_path = RAW_DIR / req.file
    if not file_path.exists():
        raise HTTPException(404, f"File not found: {req.file}")

    orch = AgentOrchestrator()

    if req.workflow == "pdf_to_word":
        orch.add_step(AgentStep("convert", "PDF转Word", "提取PDF文本并生成Word文档", pdf_to_word, {"pdf_path": str(file_path)}))
    elif req.workflow == "pdf_to_excel":
        orch.add_step(AgentStep("extract", "PDF提取表格", "从PDF中提取结构化表格数据", pdf_to_excel, {"pdf_path": str(file_path)}))
    elif req.workflow == "excel_clean":
        orch.add_step(AgentStep("load", "加载数据", "读取Excel文件", clean_excel_data, {"excel_path": str(file_path)}))
    elif req.workflow == "batch":
        orch.add_step(AgentStep("rename", "批量改名", "规范化文件名", batch_rename, {"directory": str(RAW_DIR), "pattern": "*", "prefix": "doc_"}))
        orch.add_step(AgentStep("organize", "整理归档", "按类型归类文件", organize_by_type, {"directory": str(RAW_DIR)}, depends_on=["rename"]))
    else:
        raise HTTPException(400, f"Unknown workflow: {req.workflow}")

    result = orch.run()
    return result


# ─── Dashboard data ─────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    """Get dashboard summary data."""
    return get_data_summary()


@app.get("/api/logs")
def logs(limit: int = 50):
    """Get processing logs."""
    return {"logs": get_logs(limit)}


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# ─── True Agent ────────────────────────────────────────

class AgentGoalRequest(BaseModel):
    goal: str


@app.post("/api/agent/run")
def run_true_agent(req: AgentGoalRequest):
    """Run the autonomous Agent with a user goal."""
    agent = TrueAgent()
    result = agent.run(req.goal)
    return result


@app.post("/api/agent/think")
def agent_thinking(req: AgentGoalRequest):
    """Run agent and return readable thinking log."""
    agent = TrueAgent()
    result = agent.run(req.goal)
    return {
        "thinking_log": agent.get_thinking_log(),
        "result": result,
    }
