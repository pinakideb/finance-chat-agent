"""
Routing Logic: Determines next node based on agent state
"""

from agent.agent_state import AgentState


def route_next_action(state: AgentState) -> str:
    """
    Determines the next node to visit based on current state

    Decision tree:
    1. Check iteration limit → synthesizer
    2. Check error recovery → error_handler
    3. Check replanning needed → planner
    4. Check all subtasks complete → validator or synthesizer
    5. Check validation needed → validator
    6. Continue with tool calling → tool_caller
    """

    # Safety check: iteration limit
    if state["iteration_count"] >= state["max_iterations"]:
        return "synthesizer"

    # Error recovery path
    if state["error_recovery_mode"] and state["retry_count"] < state["max_retries"]:
        return "error_handler"

    # Needs replanning
    if state["needs_replanning"]:
        return "planner"

    # Check if all subtasks are complete
    all_complete = all(
        st.status in ["completed", "failed"] for st in state["subtasks"]
    ) if state["subtasks"] else False

    # If all tasks complete
    if all_complete:
        # Check if validation is needed
        if state["needs_validation"]:
            return "validator"
        else:
            return "synthesizer"

    # Validation needed but tasks not complete yet
    # This happens after tool_caller when a validation-worthy tool was called
    # We validate first, then continue with remaining tasks
    if state["needs_validation"] and not all_complete:
        # Check if there are any HPL calculations that haven't been validated yet
        hpl_executions = [
            e for e in state["tool_executions"]
            if e.tool_name == "calculate_hypothetical_pnl"
        ]

        # If we have HPL calculations and no validation results yet
        if hpl_executions and not state["validation_results"]:
            return "validator"

    # Continue with tool calling if there are pending tasks
    if state["current_task"] or any(st.status == "pending" for st in state["subtasks"]):
        return "tool_caller"

    # Default: move to synthesis
    return "synthesizer"


def should_continue(state: AgentState) -> str:
    """
    Simple routing for END condition
    Used after synthesizer to decide whether to end
    """
    if state.get("should_continue", True) and state["iteration_count"] < state["max_iterations"]:
        return "continue"
    return "end"
