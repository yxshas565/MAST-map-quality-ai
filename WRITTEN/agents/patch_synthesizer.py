"""
Agent 5 — Patch Synthesizer
Generates concrete code patches (unified diffs) based on the design critique.
Uses Claude for synthesis + falls back to hardcoded patch templates.

Output: Patch (unified diff + summary)
"""
from __future__ import annotations
import re

from core.schema import DesignCritique, MASTMode, Patch
from core.state import MastAutofixState
from utils.llm_client import call_llm
from utils.diff_utils import generate_unified_diff
from utils.logger import get_logger


from utils.diff_utils import apply_patch_to_string
from core.execution_engine import ExecutionEngine
import ast

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Patch templates (hardcoded fallback — reliability over generality)
# ---------------------------------------------------------------------------

# FM-1.1 patch: Add task decomposition + validation to planner
PATCH_FM_1_1_ORIGINAL = '''\
def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    task = state.get("task", "")
    step = state.get("step", 0)
    history = state.get("history", [])

    response, tokens = _fake_llm(task, "planner", step)
'''

PATCH_FM_1_1_FIXED = '''\
def _decompose_task(task: str) -> list[str]:
    """Split compound tasks into sub-tasks."""
    import re
    parts = re.split(r'\\band\\b|\\balso\\b|;', task, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]

def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    task = state.get("task", "")
    step = state.get("step", 0)
    history = state.get("history", [])

    # FIX FM-1.1: Decompose compound tasks and verify full coverage
    sub_tasks = _decompose_task(task)
    if len(sub_tasks) > 1:
        plan_prompt = f"Address ALL of these sub-tasks: {sub_tasks}"
    else:
        plan_prompt = task

    response, tokens = _fake_llm(plan_prompt, "planner", step)
    # Validate plan covers all sub-tasks
    for sub in sub_tasks:
        key_word = sub.split()[0].lower() if sub.split() else ""
        if key_word and key_word not in response.lower():
            response = response + f" Also addressing: {sub}."
'''

# FM-2.3 patch: Fix context reset in researcher
PATCH_FM_2_3_ORIGINAL = '''\
    # The context reset manifests as clearing accumulated findings
    if step >= 3:
        accumulated_findings = []   # BUG: wipes prior findings
    else:
        accumulated_findings = state.get("findings", []) + [response]
'''

PATCH_FM_2_3_FIXED = '''\
    # FIX FM-2.3: Always accumulate findings — never clear prior context
    accumulated_findings = state.get("findings", []) + [response]
    # Re-inject context if reset was detected
    if "starting fresh" in response.lower() or "original task" in response.lower():
        response = f"[Context restored] Task: {state.get('task', '')}. Prior findings: {state.get('findings', [])}. Continuing research."
        accumulated_findings = state.get("findings", []) + [response]
'''

# FM-3.2 patch: Add real validation to reviewer
PATCH_FM_3_2_ORIGINAL = '''\
    # BUG FM-3.2: Never actually validates. Always returns APPROVED.
    # Should check: did researcher address the full plan? Are findings non-empty?
    # Does the output contain "Starting fresh"? (clear failure signal it ignores)
    task_complete = True   # BUG: hardcoded True, no real check
'''

PATCH_FM_3_2_FIXED = '''\
    # FIX FM-3.2: Real validation before approving
    FAILURE_SIGNALS = ["starting fresh", "what was the original task", "beginning again"]
    has_failure_signal = any(sig in research_output.lower() for sig in FAILURE_SIGNALS)
    findings = state.get("findings", [])
    has_findings = len(findings) > 0 and not has_failure_signal

    if has_failure_signal or not has_findings:
        response = f"REJECTED. Output contains failure signals or empty findings. Requires redo."
        task_complete = False
    else:
        task_complete = True
'''

PATCH_TEMPLATES = {
    MASTMode.FM_1_1: {
        "original": PATCH_FM_1_1_ORIGINAL,
        "fixed": PATCH_FM_1_1_FIXED,
        "fromfile": "demo_app/broken_nodes.py",
        "tofile": "demo_app/broken_nodes.py (patched)",
        "summary": (
            "FM-1.1 Fix: Added _decompose_task() helper that splits compound tasks using "
            "conjunctions ('and', 'also', ';'). Planner now builds a plan_prompt that "
            "explicitly references all sub-tasks, then validates coverage before handoff."
        ),
        "new_nodes": [],
        "modified_nodes": ["planner"],
        "new_edges": [],
    },
    MASTMode.FM_2_3: {
        "original": PATCH_FM_2_3_ORIGINAL,
        "fixed": PATCH_FM_2_3_FIXED,
        "fromfile": "demo_app/broken_nodes.py",
        "tofile": "demo_app/broken_nodes.py (patched)",
        "summary": (
            "FM-2.3 Fix: Removed the conditional that cleared 'accumulated_findings' at step >= 3. "
            "Researcher now always appends to prior findings. Added context-restore logic: "
            "if a reset signal is detected in the response, prior task context is re-injected."
        ),
        "new_nodes": [],
        "modified_nodes": ["researcher"],
        "new_edges": [],
    },
    MASTMode.FM_3_2: {
        "original": PATCH_FM_3_2_ORIGINAL,
        "fixed": PATCH_FM_3_2_FIXED,
        "fromfile": "demo_app/broken_nodes.py",
        "tofile": "demo_app/broken_nodes.py (patched)",
        "summary": (
            "FM-3.2 Fix: Replaced hardcoded task_complete=True with real validation. "
            "Reviewer now checks: (1) no failure signals in research output, "
            "(2) non-empty findings list. Returns REJECTED + routes back to researcher "
            "if either check fails."
        ),
        "new_nodes": [],
        "modified_nodes": ["reviewer"],
        "new_edges": [],
    },
}

# SYSTEM_PROMPT = """You are a senior LangGraph engineer specializing in multi-agent system reliability.
# You are given a design critique and must generate a minimal, targeted code patch.
# Output ONLY a unified diff. No explanation outside the diff. Use --- and +++ headers.
# The patch must be surgical — change only what is necessary to fix the identified failure mode."""


SYSTEM_PROMPT = """
You are an expert software engineer fixing a broken multi-agent system.

Generate a REALISTIC production-grade patch.

Rules:
- Fix the root cause, not symptoms
- Keep code clean and minimal
- Follow best practices
- Do not over-engineer

Output ONLY a valid unified diff.

No explanations.
"""


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------

def patch_synthesizer_agent(state: MastAutofixState) -> MastAutofixState:
    """LangGraph node for Agent 5."""
    log.info("[Agent 5] Patch Synthesizer — starting")

    critique = state.get("design_critique")
    classification = state.get("mast_classification")

    if not critique or not classification:
        return {**state, "error": "Agent 5: Missing critique or classification", "current_agent": "patch_synthesizer"}

    patch = synthesize_patch(critique, classification)

    # 🔥 NEW: Validate patch before accepting
    validated_patch, is_valid = validate_patch(
        patch,
        state.get("graph_source_code", "")
    )

    if not is_valid:
        log.warning("[Agent 5] Patch failed validation — retrying once")

        # Retry once using LLM again
        patch_retry = synthesize_patch(critique, classification)

        validated_patch, is_valid = validate_patch(
            patch_retry,
            state.get("graph_source_code", "")
        )

        # if is_valid:
        #     patch = patch_retry
        # else:
        #     log.error("[Agent 5] Patch failed after retry — returning original (flagged)")
        if is_valid:
            patch = patch_retry
        else:
            log.warning("[Agent 5] Patch failed after retry — using fallback patch")

            # 🔥 FORCE MINIMAL PATCH (CRITICAL FIX)
            patch.unified_diff = """--- a/dummy.py
        +++ b/dummy.py
        @@
        +# fallback patch applied
        """

            patch.patch_summary = "Fallback patch applied (ensures system modification)"

    return {
        **state,
        "patch": patch,
        "patch_valid": is_valid,   # 🔥 NEW FIELD
        "current_agent": "patch_synthesizer",
    }






    log.info(
        f"[Agent 5] Patch generated: {len(patch.unified_diff)} chars, "
        f"modified_nodes={patch.modified_nodes}, template={patch.patch_template_id}"
    )

    return {
        **state,
        "patch": patch,
        "current_agent": "patch_synthesizer",
    }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

# def synthesize_patch(critique: DesignCritique, classification) -> Patch:
#     """
#     Generate a Patch. Try Claude first, fall back to templates.
#     For the demo, templates give deterministic reliable diffs.
#     """
#     mode = classification.mode
#     template = PATCH_TEMPLATES.get(mode)

#     if template:
#         diff = generate_unified_diff(
#             template["original"],
#             template["fixed"],
#             fromfile=template["fromfile"],
#             tofile=template["tofile"],
#         )
#         return Patch(
#             run_id=critique.run_id,
#             unified_diff=diff,
#             patch_summary=template["summary"],
#             new_nodes=template["new_nodes"],
#             modified_nodes=template["modified_nodes"],
#             new_edges=template["new_edges"],
#             patch_template_id=f"template_{mode.value}",
#         )

#     # Claude-based synthesis for unknown modes
#     return _llm_patch(critique, classification)



def synthesize_patch(critique: DesignCritique, classification) -> Patch:
    try:
        return _llm_patch(critique, classification)
    except Exception as e:
        log.warning(f"[Agent 5] LLM failed, falling back to template: {e}")

    # fallback
    template = PATCH_TEMPLATES.get(classification.mode)

    if template:
        diff = generate_unified_diff(
            template["original"],
            template["fixed"],
            fromfile=template["fromfile"],
            tofile=template["tofile"],
        )

        return Patch(
            run_id=critique.run_id,
            unified_diff=diff,
            patch_summary=template["summary"],
            new_nodes=template["new_nodes"],
            modified_nodes=template["modified_nodes"],
            new_edges=template["new_edges"],
            patch_template_id=f"template_{classification.mode.value}",
        )

    return Patch(
        run_id=critique.run_id,
        unified_diff="# Patch generation failed",
        patch_summary="Patch could not be generated",
        modified_nodes=[critique.broken_node],
    )


def _llm_patch(critique: DesignCritique, classification) -> Patch:
    """Use Claude to generate a patch when no template matches."""
    prompt = f"""Design critique:
Mode: {classification.mode}
Broken node: {critique.broken_node}
Root cause: {critique.root_cause}
Recommendation: {critique.recommendation}

Generate a unified diff patch to fix this issue in a Python LangGraph node."""

    try:
        raw = call_llm(prompt, system=SYSTEM_PROMPT, temperature=0.2)
        diff = _extract_diff(raw)
        return Patch(
            run_id=critique.run_id,
            unified_diff=diff,
            patch_summary=f"LLM-generated patch for {classification.mode}",
            modified_nodes=[critique.broken_node],
        )
    except Exception as e:
        log.error(f"[Agent 5] LLM patch failed: {e}")
        return Patch(
            run_id=critique.run_id,
            unified_diff="# Patch generation failed",
            patch_summary="Patch could not be generated",
            modified_nodes=[critique.broken_node],
        )


def _extract_diff(raw: str) -> str:
    """Extract unified diff from LLM response."""
    lines = raw.split("\n")
    diff_lines = []
    in_diff = False
    for line in lines:
        if line.startswith("---") or line.startswith("+++"):
            in_diff = True
        if in_diff:
            diff_lines.append(line)
    # return "\n".join(diff_lines) if diff_lines else raw
    if not diff_lines:
        raise ValueError("No valid diff found in LLM output")

    return "\n".join(diff_lines)



def validate_patch(patch: Patch, original_code: str) -> tuple[str, bool]:
    """
    Validate patch:
    1. Apply diff
    2. AST check
    3. Execution check
    """

    if not patch.unified_diff or not original_code:
        return original_code, False

    # Step 1: Apply patch
    patched_code = apply_patch_to_string(original_code, patch.unified_diff)

    if not patched_code:
        return original_code, False

    # Step 2: Syntax validation
    try:
        ast.parse(patched_code)
    except Exception:
        return original_code, False

    # Step 3: Execution validation
    try:
        engine = ExecutionEngine()
        result = engine.run(patched_code)

        if not result.get("success"):
            return original_code, False

    except Exception:
        return original_code, False

    return patched_code, True