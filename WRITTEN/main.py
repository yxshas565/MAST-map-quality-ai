"""
MAST-Autofix — Main LangGraph Pipeline
Wires all 7 agents into a single graph.

Usage:
  python main.py --task "Research X and also summarize Y"
  python main.py --demo          # runs on all 4 demo tasks
"""
from __future__ import annotations
import argparse
import json

from langgraph.graph import StateGraph, END

from core.state import MastAutofixState
from agents.trace_collector import trace_collector_agent
from agents.failure_detector import failure_detector_agent
from agents.mast_classifier import mast_classifier_agent
from agents.design_critic import design_critic_agent
from agents.patch_synthesizer import patch_synthesizer_agent
from agents.evaluator import evaluator_agent
from agents.reporter import reporter_agent
from demo_app.broken_app import run_broken_app
from agents.trace_collector import demo_state_to_raw
from utils.logger import get_logger
from rich.console import Console
from agents.validator import validator_agent

log = get_logger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def route_after_failure_detection(state: MastAutofixState) -> str:
    if state.get("error"):
        return "reporter"
    if not state.get("is_failure_detected"):
        state["mast_classification"] = None
        state["design_critique"] = None
        state["patch"] = None
        state["before_benchmark"] = None
        state["after_benchmark"] = None
        return "reporter"
        
    return "mast_classifier"


def route_after_validation(state: MastAutofixState) -> str:
    if state.get("validation_passed"):
        return "reporter"

    # State was legally mutated in validator node. Just read it.
    retry_count = state.get("retry_count", 0)

    if retry_count <= 1:
        return "patch_synthesizer"

    return "reporter"


# ---------------------------------------------------------------------------
# Build the MAST-Autofix pipeline graph
# ---------------------------------------------------------------------------

def build_pipeline() -> any:
    builder = StateGraph(MastAutofixState)

    builder.add_node("trace_collector", trace_collector_agent)
    builder.add_node("failure_detector", failure_detector_agent)
    builder.add_node("mast_classifier", mast_classifier_agent)
    builder.add_node("design_critic", design_critic_agent)
    builder.add_node("patch_synthesizer", patch_synthesizer_agent)
    builder.add_node("evaluator", evaluator_agent)
    builder.add_node("reporter", reporter_agent)
    builder.add_node("validator", validator_agent)

    builder.set_entry_point("trace_collector")
    builder.add_edge("trace_collector", "failure_detector")
    builder.add_conditional_edges(
        "failure_detector",
        route_after_failure_detection,
        {"mast_classifier": "mast_classifier", "reporter": "reporter"},
    )
    builder.add_edge("mast_classifier", "design_critic")
    builder.add_edge("design_critic", "patch_synthesizer")
    # builder.add_edge("patch_synthesizer", "evaluator")
    # builder.add_edge("evaluator", "reporter")
    builder.add_edge("patch_synthesizer", "evaluator")
    builder.add_edge("evaluator", "validator")
    builder.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "patch_synthesizer": "patch_synthesizer",
            "reporter": "reporter",
        },
    )
    builder.add_edge("reporter", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# Run helper
# ---------------------------------------------------------------------------

def run_autopsy(task: str, graph_source: str = "") -> MastAutofixState:
    """Run the full MAST-Autofix pipeline on a single task."""
    console.print(f"\n[bold cyan]🔬 MAST-Autofix — Analyzing:[/bold cyan] {task}\n")

    # Step 0: Run the broken app to get a trace
    console.print("[yellow]Running broken demo app...[/yellow]")
    demo_result = run_broken_app(task)
    raw_trace = demo_state_to_raw(demo_result, task)

    # Step 1: Feed into pipeline
    initial_state: MastAutofixState = {
        "raw_trace_data": raw_trace,
        "graph_source_code": graph_source,
        "current_agent": "init",
        "retry_count": 0,
    }

    pipeline = build_pipeline()
    final_state = pipeline.invoke(initial_state)

    return final_state


def print_summary(state: MastAutofixState):
    """Print a rich summary of results to terminal."""
    report = state.get("autopsy_report")
    markdown = state.get("report_markdown", "")

    if not report:
        console.print("[red]No report generated[/red]")
        if state.get("error"):
            console.print(f"[red]Error: {state['error']}[/red]")
        return

    console.print("\n[bold green]═══ AUTOPSY COMPLETE ═══[/bold green]")
    console.print(f"[cyan]MAST Mode:[/cyan] {report.classification.mode} ({report.classification.confidence:.0%} confidence)")
    console.print(f"[cyan]Broken Node:[/cyan] {report.critique.broken_node}")
    console.print(f"[cyan]Patch:[/cyan] {report.patch.patch_summary[:100]}...")
    console.print()
    console.print(f"[bold]Benchmark Results:[/bold]")
    console.print(f"  Success Rate: {report.before_benchmark.task_success_rate:.0%} → {report.after_benchmark.task_success_rate:.0%} ({report.success_rate_delta:+.0%})")
    console.print(f"  Avg Steps:    {report.before_benchmark.avg_steps:.1f} → {report.after_benchmark.avg_steps:.1f} ({report.steps_delta:+.1f})")
    console.print(f"  Token Cost:   {report.token_cost_delta_pct:+.1f}%")
    console.print()

    # Save markdown report
    report_path = f"report_{report.run_id}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    console.print(f"[dim]Full report saved to: {report_path}[/dim]")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEMO_TASKS = [
    "Research quantum computing and also summarize recent AI breakthroughs",
    "Research the history of neural networks step by step",
    "Verify findings about quantum entanglement applications",
]

def main():
    parser = argparse.ArgumentParser(description="MAST-Autofix: Autonomous multi-agent debugger")
    parser.add_argument("--task", type=str, help="Task to analyze")
    parser.add_argument("--demo", action="store_true", help="Run all demo tasks")
    parser.add_argument("--task-index", type=int, default=0, help="Demo task index (0-2)")
    args = parser.parse_args()

    if args.demo:
        task = DEMO_TASKS[args.task_index]
    elif args.task:
        task = args.task
    else:
        task = DEMO_TASKS[0]

    state = run_autopsy(task)
    print_summary(state)


if __name__ == "__main__":
    main()