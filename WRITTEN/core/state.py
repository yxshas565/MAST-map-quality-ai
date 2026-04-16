"""
LangGraph pipeline state — the single TypedDict that flows through all 7 agents.
"""
from __future__ import annotations
from typing import Any, Optional
from typing_extensions import TypedDict

from core.schema import (
    RunTrace, FailureWindow, MASTClassification,
    DesignCritique, Patch, BenchmarkResult, AutopsyReport
)


class MastAutofixState(TypedDict, total=False):
    # --- Input ---
    raw_trace_data: dict[str, Any]      # raw JSON from LangGraph callback hooks
    graph_source_code: str              # source of the LangGraph app being analyzed

    # --- Agent 1: Trace Collector ---
    run_trace: RunTrace

    # --- Agent 2: Failure Detector ---
    failure_window: FailureWindow
    is_failure_detected: bool

    # --- Agent 3: MAST Classifier ---
    mast_classification: MASTClassification

    # --- Agent 4: Design Critic ---
    design_critique: DesignCritique

    # --- Agent 5: Patch Synthesizer ---
    patch: Patch

    # --- Agent 6: Evaluator ---
    before_benchmark: BenchmarkResult
    after_benchmark: BenchmarkResult

    # --- Agent 7: Reporter ---
    autopsy_report: AutopsyReport
    report_markdown: str                # final human-readable report

    # --- Pipeline control ---
    error: Optional[str]                # propagated error message if any step fails
    current_agent: str                  # for UI progress tracking

    # --- Validation / Control Layer ---
    validation_passed: bool
    retry_count: int
    evaluation_details: dict[str, Any]