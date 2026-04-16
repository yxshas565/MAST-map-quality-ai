# """
# Agent 3 — MAST Classifier
# The heart of the pipeline. Uses Claude (few-shot prompting) to classify
# the failure window into one of 3 MAST failure modes.

# Modes implemented:
#   FM-1.1  Disobey Task Specification
#   FM-2.3  Conversation Reset
#   FM-3.2  Incomplete Verification

# Output: MASTClassification
# """
# from __future__ import annotations
# import json
# import re

# from core.schema import FailureWindow, MASTClassification, MASTMode
# from core.config import MIN_CONFIDENCE_FOR_PATCH
# from core.state import MastAutofixState
# from utils.llm_client import call_llm
# from utils.logger import get_logger

# log = get_logger(__name__)


# # ---------------------------------------------------------------------------
# # Few-shot examples (the key to accurate zero-training classification)
# # ---------------------------------------------------------------------------

# FEW_SHOT_EXAMPLES = """
# EXAMPLE 1:
# Failure window:
#   planner [step 0]: input="Research X and also summarize Y" → output="Plan: I will only address the first part of this request."
#   researcher [step 1]: output="Research findings for step 1: [data point 1]"
#   reviewer [step 2]: output="APPROVED. Task complete."
# Classification: {"mode": "FM-1.1", "confidence": 0.91, "affected_node": "planner", "reasoning": "The planner explicitly acknowledges only addressing the first part of a compound task, discarding the second instruction. This is a direct violation of task specification — FM-1.1."}

# EXAMPLE 2:
# Failure window:
#   researcher [step 1]: output="Research findings for step 1: [data point 1], [source 1]"
#   researcher [step 2]: output="Research findings for step 2: [data point 2], [source 2]"
#   researcher [step 3]: output="Starting fresh research. What was the original task again?"
# Classification: {"mode": "FM-2.3", "confidence": 0.95, "affected_node": "researcher", "reasoning": "The researcher discards all prior context at step 3 and resets to the beginning. This is a conversation context reset — FM-2.3. The agent loses memory of accumulated findings and re-asks for the task."}

# EXAMPLE 3:
# Failure window:
#   researcher [step 3]: output="Starting fresh research. What was the original task again?"
#   reviewer [step 4]: input="Starting fresh research. What was the original task again?" → output="APPROVED. Task complete."
# Classification: {"mode": "FM-3.2", "confidence": 0.88, "affected_node": "reviewer", "reasoning": "The reviewer approves an output that contains an explicit failure signal ('Starting fresh research'). The reviewer performs no validation of correctness or completeness, rubber-stamping a clearly incomplete result. This is FM-3.2 — Incomplete Verification."}
# """

# SYSTEM_PROMPT = """You are MAST-Classifier, an expert at diagnosing multi-agent LLM system failures using the MAST taxonomy.

# The MAST taxonomy defines failure modes for multi-agent systems. You must classify failure windows into one of these modes:

# FM-1.1 — Disobey Task Specification
#   The agent ignores, truncates, or misinterprets part of the task it was given.
#   Signal: Agent output covers only a subset of a multi-part instruction. Agent says "only the first part" or similar.

# FM-2.3 — Conversation Reset  
#   An agent loses its conversation context mid-run and starts over from scratch.
#   Signal: "Starting fresh", "What was the original task", agent output forgets prior accumulated state.

# FM-3.2 — Incomplete Verification
#   A verification/review agent approves output without actually checking its correctness or completeness.
#   Signal: Reviewer outputs APPROVED even when input contains failure signals, reset keywords, or incomplete data.

# UNKNOWN — None of the above applies clearly.

# You will be given a failure window (last N steps of a broken run).
# Respond ONLY with a valid JSON object. No explanation outside the JSON.
# JSON format: {"mode": "FM-X.X", "confidence": 0.0-1.0, "affected_node": "node_name", "reasoning": "..."}
# """


# # ---------------------------------------------------------------------------
# # Main agent function
# # ---------------------------------------------------------------------------

# def mast_classifier_agent(state: MastAutofixState) -> MastAutofixState:
#     """LangGraph node for Agent 3."""
#     log.info("[Agent 3] MAST Classifier — starting")

#     failure_window = state.get("failure_window")
#     if not failure_window or not state.get("is_failure_detected"):
#         log.info("[Agent 3] No failure to classify")
#         return {**state, "current_agent": "mast_classifier"}

#     classification = classify_failure(failure_window)

#     log.info(
#         f"[Agent 3] Classification: {classification.mode} "
#         f"(confidence={classification.confidence:.2f}, node={classification.affected_node})"
#     )

#     if classification.confidence < MIN_CONFIDENCE_FOR_PATCH:
#         log.warning(f"[Agent 3] Confidence {classification.confidence:.2f} below threshold — patch may be skipped")

#     return {
#         **state,
#         "mast_classification": classification,
#         "current_agent": "mast_classifier",
#     }


# # ---------------------------------------------------------------------------
# # Core classification logic
# # ---------------------------------------------------------------------------

# def classify_failure(window: FailureWindow) -> MASTClassification:
#     """
#     Run few-shot classification on the failure window.
#     Returns MASTClassification.
#     """
#     window_text = _format_window_for_prompt(window)

#     prompt = f"""Here are few-shot examples of MAST classification:

# {FEW_SHOT_EXAMPLES}

# Now classify this failure window:
# {window_text}

# Respond with ONLY a JSON object in the format shown in the examples."""

#     try:
#         raw_response = call_llm(prompt, system=SYSTEM_PROMPT, temperature=0.1)
#         return _parse_classification(raw_response, window)
#     except Exception as e:
#         log.error(f"[Agent 3] LLM call failed: {e}")
#         return _fallback_classification(window)


# def _format_window_for_prompt(window: FailureWindow) -> str:
#     """Convert FailureWindow into a readable text block for the prompt."""
#     lines = [f"Failure type: {window.failure_type}", f"Error: {window.error_message}", "Steps:"]
#     for step in window.window_steps:
#         input_text = step.input_state.get("input", "")[:100]
#         output_text = step.output_state.get("output", "")[:150]
#         lines.append(
#             f"  {step.node_name} [step {step.step_index}]: "
#             f"input=\"{input_text}\" → output=\"{output_text}\""
#         )
#     return "\n".join(lines)


# def _parse_classification(raw: str, window: FailureWindow) -> MASTClassification:
#     """Parse LLM JSON response into MASTClassification."""
#     # Strip any markdown fences
#     clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

#     try:
#         data = json.loads(clean)
#     except json.JSONDecodeError:
#         # Try to extract JSON from within the response
#         match = re.search(r'\{.*\}', clean, re.DOTALL)
#         if match:
#             data = json.loads(match.group())
#         else:
#             log.error(f"[Agent 3] Could not parse JSON from: {raw[:200]}")
#             return _fallback_classification(window)

#     mode_str = data.get("mode", "UNKNOWN")
#     try:
#         mode = MASTMode(mode_str)
#     except ValueError:
#         mode = MASTMode.UNKNOWN

#     return MASTClassification(
#         run_id=window.run_id,
#         mode=mode,
#         confidence=float(data.get("confidence", 0.5)),
#         reasoning=data.get("reasoning", "No reasoning provided"),
#         affected_node=data.get("affected_node", window.failure_node),
#     )


# def _fallback_classification(window: FailureWindow) -> MASTClassification:
#     """
#     Rule-based fallback if LLM is unavailable.
#     Covers the 2 most common modes deterministically.
#     """
#     error_msg = window.error_message.lower()

#     if "context reset" in error_msg or "starting fresh" in error_msg:
#         return MASTClassification(
#             run_id=window.run_id,
#             mode=MASTMode.FM_2_3,
#             confidence=0.80,
#             reasoning="Rule-based fallback: detected context reset keywords in failure message",
#             affected_node=window.failure_node,
#         )
#     elif "spec violation" in error_msg or "first part" in error_msg:
#         return MASTClassification(
#             run_id=window.run_id,
#             mode=MASTMode.FM_1_1,
#             confidence=0.75,
#             reasoning="Rule-based fallback: detected task specification violation keywords",
#             affected_node=window.failure_node,
#         )
#     elif "incomplete verification" in error_msg or "approved" in error_msg:
#         return MASTClassification(
#             run_id=window.run_id,
#             mode=MASTMode.FM_3_2,
#             confidence=0.75,
#             reasoning="Rule-based fallback: detected incomplete verification signal",
#             affected_node=window.failure_node,
#         )
#     else:
#         return MASTClassification(
#             run_id=window.run_id,
#             mode=MASTMode.UNKNOWN,
#             confidence=0.40,
#             reasoning="Could not classify — LLM unavailable and no rule matched",
#             affected_node=window.failure_node,
#         )


































"""
Agent 3 — MAST Classifier
Uses real LLM (HuggingFace free or Anthropic) with few-shot prompting.
Falls back to rule-based if no key available.
"""
from __future__ import annotations
import json
import re
import os

from core.schema import FailureWindow, MASTClassification, MASTMode
from core.config import MIN_CONFIDENCE_FOR_PATCH
from core.state import MastAutofixState
from utils.logger import get_logger

log = get_logger(__name__)

# ── Few-shot examples ────────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = """
EXAMPLE 1:
Failure window:
  planner [step 0]: input="Research X and also summarize Y" -> output="Plan: I will only address the first part of this request."
  researcher [step 1]: output="Research findings for step 1"
  reviewer [step 2]: output="APPROVED. Task complete."
Output: {"mode": "FM-1.1", "confidence": 0.91, "affected_node": "planner", "reasoning": "Planner explicitly states it will only address the first part of a compound task, discarding the second instruction. Direct FM-1.1 violation."}

EXAMPLE 2:
Failure window:
  researcher [step 1]: output="Research findings for step 1: [data]"
  researcher [step 2]: output="Research findings for step 2: [data]"
  researcher [step 3]: output="Starting fresh research. What was the original task again?"
Output: {"mode": "FM-2.3", "confidence": 0.95, "affected_node": "researcher", "reasoning": "Researcher discards all prior context at step 3 and resets. Classic FM-2.3 conversation reset."}

EXAMPLE 3:
Failure window:
  researcher [step 3]: output="Starting fresh research. What was the original task again?"
  reviewer [step 4]: input="Starting fresh..." -> output="APPROVED. Task complete."
Output: {"mode": "FM-3.2", "confidence": 0.88, "affected_node": "reviewer", "reasoning": "Reviewer approves despite obvious failure signal in input. No validation performed. FM-3.2 incomplete verification."}
"""

# SYSTEM_PROMPT = """You are MAST-Classifier, an expert at diagnosing multi-agent LLM failures.

# Classify the failure into exactly one mode:
# - FM-1.1: Agent ignores/truncates part of the task specification
# - FM-2.3: Agent loses conversation context and resets mid-run
# - FM-3.2: Verification agent approves without actually checking output
# - UNKNOWN: None of the above

# Respond ONLY with a JSON object. No text before or after.
# Format: {"mode": "FM-X.X", "confidence": 0.0-1.0, "affected_node": "name", "reasoning": "..."}"""

SYSTEM_PROMPT = """
You are a world-class expert in debugging multi-agent AI systems.

Your task:
- Identify the exact failure mode using the MAST taxonomy.
- Think step-by-step internally, but output only the final reasoning.

Be extremely precise:
- Mention exact violation
- Reference specific behavior
- Explain downstream impact

Output STRICT JSON:
{
  "mode": "...",
  "confidence": 0.0-1.0,
  "affected_node": "...",
  "reasoning": "..."
}
"""


# ── Main agent function ──────────────────────────────────────────────────────

def mast_classifier_agent(state: MastAutofixState) -> MastAutofixState:
    log.info("[Agent 3] MAST Classifier — starting")

    failure_window = state.get("failure_window")
    
    if not failure_window or not state.get("is_failure_detected"):
        log.info("[Agent 3] No failure to classify")
        return {**state, "current_agent": "mast_classifier"}

    classification = classify_failure(failure_window)

    log.info(
        f"[Agent 3] {classification.mode} "
        f"(confidence={classification.confidence:.0%}, node={classification.affected_node})"
    )
    return {**state, "mast_classification": classification, "current_agent": "mast_classifier"}


# ── Core classification ──────────────────────────────────────────────────────

def classify_failure(window: FailureWindow) -> MASTClassification:
    """Try LLM first, fall back to rules if unavailable."""

    # Check which provider is available
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    has_hf = bool(os.environ.get("HF_TOKEN", ""))

    if has_anthropic or has_hf:
        try:
            return _llm_classify(window)
        except Exception as e:
            log.warning(f"[Agent 3] LLM failed ({e}), using rule-based fallback")

    log.info("[Agent 3] Using rule-based fallback (set HF_TOKEN in .env for real LLM)")
    return _fallback_classification(window)


def _llm_classify(window: FailureWindow) -> MASTClassification:
    from utils.llm_client import call_llm

    window_text = _format_window(window)
    prompt = f"""{FEW_SHOT_EXAMPLES}

Now classify this failure window:
{window_text}

Respond with ONLY a JSON object."""

    raw = call_llm(prompt, system=SYSTEM_PROMPT, temperature=0.1, max_tokens=512)
    return _parse_response(raw, window)


def _format_window(window: FailureWindow) -> str:
    lines = [
        f"Failure type: {window.failure_type}",
        f"Error message: {window.error_message}",
        "Steps:"
    ]
    for step in window.window_steps:
        inp = step.input_state.get("input", "")[:100]
        out = step.output_state.get("output", "")[:150]
        lines.append(f"  {step.node_name} [step {step.step_index}]: input=\"{inp}\" -> output=\"{out}\"")
    return "\n".join(lines)


def _parse_response(raw: str, window: FailureWindow) -> MASTClassification:
    # Strip markdown fences
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()

    # Extract JSON object
    match = re.search(r'\{[^{}]+\}', clean, re.DOTALL)
    if not match:
        log.error(f"[Agent 3] No JSON found in: {raw[:200]}")
        return _fallback_classification(window)

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        log.error(f"[Agent 3] JSON parse error: {e}")
        return _fallback_classification(window)

    try:
        mode = MASTMode(data.get("mode", "UNKNOWN"))
    except ValueError:
        mode = MASTMode.UNKNOWN

    return MASTClassification(
        run_id=window.run_id,
        mode=mode,
        confidence=float(data.get("confidence", 0.5)),
        reasoning=data.get("reasoning", "No reasoning provided"),
        affected_node=data.get("affected_node", window.failure_node),
    )


def _fallback_classification(window: FailureWindow) -> MASTClassification:
    """Rule-based fallback — deterministic, no API needed."""
    msg = window.error_message.lower()

    # Check window step outputs for signals
    all_outputs = " ".join(
        s.output_state.get("output", "").lower()
        for s in window.window_steps
    )

    if "only address the first part" in all_outputs or "spec violation" in msg or "first part" in msg:
        return MASTClassification(run_id=window.run_id, mode=MASTMode.FM_1_1,
            confidence=0.80, affected_node=window.failure_node,
            reasoning="Rule-based: task specification violation detected in planner output")

    if "starting fresh" in all_outputs or "original task" in all_outputs or "context reset" in msg:
        return MASTClassification(run_id=window.run_id, mode=MASTMode.FM_2_3,
            confidence=0.80, affected_node=window.failure_node,
            reasoning="Rule-based: context reset signal detected in researcher output")

    if "incomplete verification" in msg or ("approved" in all_outputs and "starting fresh" in all_outputs):
        return MASTClassification(run_id=window.run_id, mode=MASTMode.FM_3_2,
            confidence=0.80, affected_node=window.failure_node,
            reasoning="Rule-based: reviewer approved despite failure signals in input")

    return MASTClassification(run_id=window.run_id, mode=MASTMode.UNKNOWN,
        confidence=0.40, affected_node=window.failure_node,
        reasoning="No rule matched — set HF_TOKEN or ANTHROPIC_API_KEY for LLM classification")