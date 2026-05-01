"""Office Agent v2 - Configuration"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = DATA_DIR / "logs"

for d in [RAW_DIR, PROCESSED_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# LLM Configuration
# Supports: deepseek, openai, ollama
# Set env vars: OA_LLM_PROVIDER, OA_API_KEY, OA_BASE_URL, OA_MODEL
LLM_PROVIDER = os.getenv("OA_LLM_PROVIDER", "deepseek")
LLM_API_KEY = os.getenv("OA_API_KEY", "")
LLM_BASE_URL = os.getenv("OA_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("OA_MODEL", "deepseek-chat")

# Fallback to local ollama if no API key
if not LLM_API_KEY:
    LLM_PROVIDER = "ollama"
    LLM_BASE_URL = "http://localhost:11434/v1"
    LLM_MODEL = "qwen2.5:7b"

# UI
UI_PORT = int(os.getenv("OA_UI_PORT", "8501"))
API_PORT = int(os.getenv("OA_API_PORT", "8000"))
