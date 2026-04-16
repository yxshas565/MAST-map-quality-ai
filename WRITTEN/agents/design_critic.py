"""
Agent 4 — Design Critic
Takes the MAST classification + graph topology → architectural diagnosis.
Points to the exact broken node/edge with a human-readable critique.

Output: DesignCritique
"""
from __future__ import annotations

from core.schema import MASTClassification, MASTMode, DesignCritique
from core.state import MastAutofixState
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Critique templates per MAST mode
# ---------------------------------------------------------------------------

CRITIQUES = {
    MASTMode.FM_1_1: {
        "root_cause": (
            "The planner node processes compound instructions by silently truncating them. "
            "When a task contains conjunctions ('and', 'also'), the planner only acts on the "
            "first clause, discarding the rest without raising an error or notifying downstream agents. "
            "This is a prompt-level failure — the node's instruction set doesn't enforce full-task coverage."
        ),
        "recommendation": (
            "Add a task decomposition step inside the planner: parse the task into sub-tasks, "
            "verify all sub-tasks are represented in the plan, and only proceed if the plan "
            "covers 100% of the original specification. Inject a validation check before handing off to researcher."
        ),
        "broken_node": "planner",
        "broken_edge": None,
    },
    MASTMode.FM_2_3: {
        "root_cause": (
            "The researcher node does not persist accumulated context across loop iterations. "
            "After a fixed number of steps, the node's internal state is wiped, causing it to "
            "lose all prior findings and restart from scratch. This is an architectural flaw — "
            "the graph state schema does not enforce that 'findings' accumulate across researcher calls."
        ),
        "recommendation": (
            "Introduce a stateful 'context_store' node or move accumulated findings into "
            "the graph state as an append-only list. Add a context_guard node between "
            "reviewer → researcher that re-injects prior findings before each researcher call. "
            "Alternatively, fix the researcher node to never clear findings regardless of step count."
        ),
        "broken_node": "researcher",
        "broken_edge": ("reviewer", "researcher"),
    },
    MASTMode.FM_3_2: {
        "root_cause": (
            "The reviewer node performs no semantic validation of the research output. "
            "It outputs APPROVED unconditionally, regardless of whether the input contains "
            "failure signals (context resets, empty findings, task incompleteness). "
            "The routing logic depends entirely on the reviewer's verdict — since the reviewer "
            "always approves, the loop terminates on invalid outputs."
        ),
        "recommendation": (
            "Replace the stub reviewer with a real validation node that checks: "
            "(1) research output is non-empty, (2) no reset keywords present, "
            "(3) all plan sub-tasks are addressed in findings. "
            "Add a 'validator' node upstream of reviewer that enforces these contracts "
            "and can route back to planner for a full restart if validation fails."
        ),
        "broken_node": "reviewer",
        "broken_edge": ("reviewer", "__end__"),
    },
    MASTMode.UNKNOWN: {
        "root_cause": "Failure mode could not be classified with sufficient confidence.",
        "recommendation": "Inspect the raw trace manually. Consider adding more detailed error logging to each node.",
        "broken_node": "unknown",
        "broken_edge": None,
    },
}


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------

def design_critic_agent(state: MastAutofixState) -> MastAutofixState:
    """LangGraph node for Agent 4."""
    log.info("[Agent 4] Design Critic — starting")

    classification = state.get("mast_classification")
    if not classification:
        return {**state, "error": "Agent 4: No classification in state", "current_agent": "design_critic"}

    critique = generate_critique(classification)

    log.info(
        f"[Agent 4] Critique: broken_node='{critique.broken_node}', "
        f"mode={critique.mast_mode}"
    )

    return {
        **state,
        "design_critique": critique,
        "current_agent": "design_critic",
    }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

# def generate_critique(classification: MASTClassification) -> DesignCritique:
#     """Generate a DesignCritique from a MASTClassification."""
#     template = CRITIQUES.get(classification.mode, CRITIQUES[MASTMode.UNKNOWN])

#     # Override broken_node with what the classifier identified if it's more specific
#     broken_node = classification.affected_node or template["broken_node"]

#     return DesignCritique(
#         run_id=classification.run_id,
#         mast_mode=classification.mode,
#         root_cause=template["root_cause"],
#         broken_node=broken_node,
#         broken_edge=template.get("broken_edge"),
#         recommendation=template["recommendation"],
#     )



from utils.llm_client import call_llm
import json

# SYSTEM_PROMPT = """You are an expert in debugging LangGraph multi-agent systems.
# Given a failure classification, produce a root cause and recommendation.

# Respond ONLY in JSON:
# {
#   "root_cause": "...",
#   "recommendation": "...",
#   "broken_node": "..."
# }
# """

SYSTEM_PROMPT = """
You are a senior AI systems architect diagnosing production failures.

Your job:
- Identify the REAL root cause (not symptoms)
- Explain WHY the system failed
- Propose a FIX that would work in production

Be sharp, technical, and confident.

Avoid generic statements.
Focus on:
- system design flaws
- state management issues
- execution logic

Return STRICT JSON:
{
  "root_cause": "...",
  "recommendation": "...",
  "broken_node": "..."
}
"""



# def generate_critique(classification: MASTClassification) -> DesignCritique:
#     prompt = f"""
# Mode: {classification.mode}
# Affected node: {classification.affected_node}
# Confidence: {classification.confidence}

# Explain:
# 1. Root cause of failure
# 2. How to fix it architecturally
# """

#     try:
#         raw = call_llm(prompt, system=SYSTEM_PROMPT, temperature=0.2)
#         data = json.loads(raw)

#         return DesignCritique(
#             run_id=classification.run_id,
#             mast_mode=classification.mode,
#             root_cause=data.get("root_cause", ""),
#             recommendation=data.get("recommendation", ""),
#             broken_node=data.get("broken_node", classification.affected_node),
#             broken_edge=None,
#         )

#     except Exception as e:
#         log.warning(f"[Agent 4] LLM failed, using template fallback: {e}")

#         template = CRITIQUES.get(classification.mode, CRITIQUES[MASTMode.UNKNOWN])
#         return DesignCritique(
#             run_id=classification.run_id,
#             mast_mode=classification.mode,
#             root_cause=template["root_cause"],
#             recommendation=template["recommendation"],
#             broken_node=classification.affected_node or template["broken_node"],
#             broken_edge=template.get("broken_edge"),
#         )


import re

def _extract_json(text: str) -> dict:
    """Extract JSON safely from LLM response."""
    try:
        # Extract JSON block using regex
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


def generate_critique(classification: MASTClassification) -> DesignCritique:
    prompt = f"""
Mode: {classification.mode}
Affected node: {classification.affected_node}
Confidence: {classification.confidence}

Explain clearly:
1. Root cause
2. Architectural fix

Return ONLY JSON.
"""

    try:
        raw = call_llm(prompt, system=SYSTEM_PROMPT, temperature=0.2)

        data = _extract_json(raw)

        # ✅ Fallback only if parsing failed badly
        if not data:
            raise ValueError("No JSON extracted")

        return DesignCritique(
            run_id=classification.run_id,
            mast_mode=classification.mode,
            root_cause=data.get("root_cause", "LLM analysis unavailable"),
            recommendation=data.get("recommendation", "No recommendation provided"),
            broken_node=data.get("broken_node", classification.affected_node),
            broken_edge=None,
        )

    except Exception as e:
        log.warning(f"[Agent 4] LLM parsing failed, using template fallback: {e}")

        template = CRITIQUES.get(classification.mode, CRITIQUES[MASTMode.UNKNOWN])
        return DesignCritique(
            run_id=classification.run_id,
            mast_mode=classification.mode,
            root_cause=template["root_cause"],
            recommendation=template["recommendation"],
            broken_node=classification.affected_node or template["broken_node"],
            broken_edge=template.get("broken_edge"),
        )