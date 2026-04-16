"""
Global configuration — loaded once at startup.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# === LLM ===
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
HF_TOKEN: str = os.environ.get("HF_TOKEN", "")

# Model tiers — always use CHEAP for this project
PRIMARY_MODEL: str = "claude-haiku-4-5-20251001"   # ~$0.001 per classification
FALLBACK_MODEL: str = "gpt-4o-mini"

# === LangSmith ===
LANGCHAIN_TRACING_V2: bool = os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_PROJECT: str = os.environ.get("LANGCHAIN_PROJECT", "mast-autofix")

# === Benchmark ===
BENCHMARK_TASKS_DIR: str = os.environ.get("BENCHMARK_TASKS_DIR", "benchmark/tasks")
BENCHMARK_RESULTS_DIR: str = os.environ.get("BENCHMARK_RESULTS_DIR", "benchmark/results")
BENCHMARK_NUM_TASKS: int = int(os.environ.get("BENCHMARK_NUM_TASKS", "15"))

# === Failure detection thresholds ===
MAX_STEPS_BEFORE_TIMEOUT: int = 25
FAILURE_WINDOW_SIZE: int = 5
MIN_CONFIDENCE_FOR_PATCH: float = 0.65

# === Logging ===
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")