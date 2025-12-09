"""
Error Handler Node: Implements retry logic with alternative approaches
"""

from agent.agent_state import AgentState, create_reasoning_step


async def handle_errors(state: AgentState) -> dict:
    """
    Attempts error recovery through retries and alternative strategies
    """

    latest_error = state["errors"][-1] if state["errors"] else None

    if not latest_error:
        return {
            "error_recovery_mode": False,
            "iteration_count": state["iteration_count"] + 1
        }

    retry_count = state["retry_count"]

    # Reasoning about error
    reasoning = create_reasoning_step(
        step_type="error",
        content=f"Encountered error: {latest_error['error']}. Attempting recovery (retry {retry_count}/{state['max_retries']})",
        metadata=latest_error
    )

    # Strategy 1: Retry with same parameters (transient errors)
    if retry_count == 0:
        return {
            "retry_count": retry_count + 1,
            "reasoning_steps": [reasoning],
            "should_continue": True,
            "needs_replanning": False,
            "iteration_count": state["iteration_count"] + 1
        }

    # Strategy 2: Try alternative tool (if available)
    elif retry_count == 1:
        # Find failed subtask
        failed_subtask = None
        for st in state["subtasks"]:
            if st.id == latest_error["subtask_id"]:
                failed_subtask = st
                break

        if failed_subtask and len(failed_subtask.assigned_tools) > 1:
            # Switch to alternative tool
            alt_reasoning = create_reasoning_step(
                step_type="error",
                content="Trying alternative tool approach",
                metadata={"strategy": "alternative_tool", "subtask": failed_subtask.id}
            )
            return {
                "retry_count": retry_count + 1,
                "reasoning_steps": [reasoning, alt_reasoning],
                "current_task": failed_subtask.id,
                "should_continue": True,
                "iteration_count": state["iteration_count"] + 1
            }
        else:
            # No alternative tool available, skip to next strategy
            return {
                "retry_count": retry_count + 2,  # Skip strategy 2
                "reasoning_steps": [reasoning],
                "should_continue": True,
                "iteration_count": state["iteration_count"] + 1
            }

    # Strategy 3: Replan with different subtasks
    elif retry_count == 2:
        replan_reasoning = create_reasoning_step(
            step_type="error",
            content="Replanning query with different approach",
            metadata={"strategy": "replan"}
        )
        return {
            "retry_count": retry_count + 1,
            "reasoning_steps": [reasoning, replan_reasoning],
            "needs_replanning": True,
            "should_continue": True,
            "iteration_count": state["iteration_count"] + 1
        }

    # Give up after max retries
    final_reasoning = create_reasoning_step(
        step_type="error",
        content="Max retries exceeded. Proceeding with partial results.",
        metadata={"strategy": "give_up", "retry_count": retry_count}
    )
    return {
        "error_recovery_mode": False,
        "reasoning_steps": [reasoning, final_reasoning],
        "should_continue": True,
        "iteration_count": state["iteration_count"] + 1
    }
