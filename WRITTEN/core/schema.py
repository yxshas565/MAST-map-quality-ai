"""
Shared data models for the entire MAST-Autofix pipeline.
All agents speak this language.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# MAST failure mode taxonomy (subset — the 3 we implement)
# ---------------------------------------------------------------------------

class MASTMode(str, Enum):
    FM_1_1 = "FM-1.1"   # Disobey Task Specification
    FM_2_3 = "FM-2.3"   # Conversation Reset
    FM_3_2 = "FM-3.2"   # Incomplete Verification
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Trace-level primitives
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    name: str
    input: dict[str, Any]
    output: Any
    error: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class NodeExecution:
    node_name: str
    step_index: int
    input_state: dict[str, Any]
    output_state: dict[str, Any]
    tool_calls: list[ToolCall] = field(default_factory=list)
    error: Optional[str] = None
    latency_ms: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)  # {prompt, completion, total}


@dataclass
class RunTrace:
    run_id: str
    graph_name: str
    task: str
    nodes: list[NodeExecution] = field(default_factory=list)
    final_output: Any = None
    total_steps: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Failure detection output
# ---------------------------------------------------------------------------

@dataclass
class FailureWindow:
    run_id: str
    failure_type: str           # "exception" | "timeout" | "contract_violation"
    failure_node: str           # which node triggered it
    window_steps: list[NodeExecution]   # last N steps
    error_message: str = ""


# ---------------------------------------------------------------------------
# MAST classification output
# ---------------------------------------------------------------------------

@dataclass
class MASTClassification:
    run_id: str
    mode: MASTMode
    confidence: float           # 0.0 – 1.0
    reasoning: str              # LLM's explanation
    affected_node: str          # which node/edge is to blame
    affected_edge: Optional[tuple[str, str]] = None


# ---------------------------------------------------------------------------
# Design critic output
# ---------------------------------------------------------------------------

@dataclass
class DesignCritique:
    run_id: str
    mast_mode: MASTMode
    root_cause: str             # human-readable diagnosis
    broken_node: str
    broken_edge: Optional[tuple[str, str]]
    recommendation: str         # what to change


# ---------------------------------------------------------------------------
# Patch synthesizer output
# ---------------------------------------------------------------------------

@dataclass
class Patch:
    run_id: str
    unified_diff: str           # actual unified diff string
    patch_summary: str          # natural language description
    new_nodes: list[str] = field(default_factory=list)
    modified_nodes: list[str] = field(default_factory=list)
    new_edges: list[tuple[str, str]] = field(default_factory=list)
    patch_template_id: Optional[str] = None    # which template was used


# ---------------------------------------------------------------------------
# Benchmark / evaluator output
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    run_id: str
    is_patched: bool
    task_success_rate: float    # 0.0 – 1.0
    avg_steps: float
    avg_tokens: float
    avg_latency_ms: float
    num_tasks: int


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

@dataclass
class AutopsyReport:
    run_id: str
    graph_name: str
    task: str
    failure_window: FailureWindow
    classification: MASTClassification
    critique: DesignCritique
    patch: Patch
    before_benchmark: BenchmarkResult
    after_benchmark: BenchmarkResult

    @property
    def success_rate_delta(self) -> float:
        return self.after_benchmark.task_success_rate - self.before_benchmark.task_success_rate

    @property
    def steps_delta(self) -> float:
        return self.after_benchmark.avg_steps - self.before_benchmark.avg_steps

    @property
    def token_cost_delta_pct(self) -> float:
        if self.before_benchmark.avg_tokens == 0:
            return 0.0
        return (self.after_benchmark.avg_tokens - self.before_benchmark.avg_tokens) / self.before_benchmark.avg_tokens * 100