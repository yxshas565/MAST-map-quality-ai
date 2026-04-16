from core.state import MastAutofixState
from utils.logger import get_logger

log = get_logger(__name__)

def validator_agent(state: MastAutofixState) -> MastAutofixState:
    """Validates whether patch actually improved system."""

    before = state.get("before_benchmark")
    after = state.get("after_benchmark")

    if not before or not after:
        return {
            **state,
            "validation_passed": False,
            "validation_reason": "Missing benchmark data",
            "current_agent": "validator"
        }

    before_score = before.task_success_rate
    after_score = after.task_success_rate

    # 🔥 Core validation logic
    if after_score > before_score:
        log.info("[Validator] Patch improved system ✅")
        return {
            **state,
            "validation_passed": True,
            "validation_reason": "Improved success rate",
            "current_agent": "validator"
        }

    elif after_score == before_score:
        log.warning("[Validator] No improvement ⚠️")
        return {
            **state,
            "validation_passed": False,
            "validation_reason": "No improvement",
            "retry_count": state.get("retry_count", 0) + 1,
            "current_agent": "validator"
        }

    else:
        log.error("[Validator] Patch made things worse ❌")
        return {
            **state,
            "validation_passed": False,
            "validation_reason": "Regression detected",
            "retry_count": state.get("retry_count", 0) + 1,
            "current_agent": "validator"
        }