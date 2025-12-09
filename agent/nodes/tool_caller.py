"""
Tool Caller Node: Executes MCP tools based on current subtask
"""

import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from agent.agent_state import AgentState, create_tool_execution, create_reasoning_step


def create_tool_caller(mcp_manager):
    """
    Factory function that creates a tool_caller node with MCP manager in closure
    This avoids state serialization issues
    """

    async def execute_tools(state: AgentState) -> dict:
        """
        Executes tools for the current subtask
        Handles tool selection, argument preparation, and execution
        """

        # Find current subtask
        current_subtask = None
        for st in state["subtasks"]:
            if st.id == state["current_task"]:
                current_subtask = st
                break

        if not current_subtask:
            # No current task - move to next pending subtask
            for st in state["subtasks"]:
                if st.status == "pending":
                    return {
                        "current_task": st.id,
                        "iteration_count": state["iteration_count"] + 1
                    }
            # No more tasks
            return {
                "should_continue": False,
                "iteration_count": state["iteration_count"] + 1
            }

        # Mark subtask as in progress
        current_subtask.status = "in_progress"

        # Build context from previous results
        context_str = ""
        if state["intermediate_results"]:
            context_str = "\n\nPrevious results:\n"
            for task_id, result in state["intermediate_results"].items():
                context_str += f"- {task_id}: {result}\n"

        # Use LLM to determine exact tool calls needed
        tool_selection_prompt = f"""You are executing a subtask in a multi-step workflow.

Current subtask: {current_subtask.description}
Assigned tools: {current_subtask.assigned_tools}
{context_str}

Original query: {state['original_query']}

Based on this subtask, determine which tool to call and with what arguments.

Available tools and their EXACT parameters (use these exact names):
- get_hpl_formula(hierarchy: str) - hierarchy must be "FHC" or "PRA"
- update_hpl_formula(hierarchy: str, new_formula: str) - IMPORTANT: parameter is "new_formula" not "formula". The formula MUST include the full equation with "Hypothetical P&L = " on the left side.
- get_all_hierarchies() - no parameters
- get_all_accounts() - no parameters
- get_account_pnl(account_number: str) - provide account number like "ACCT-001"
- calculate_hypothetical_pnl(account_number: str, hierarchy: str) - provide account number and hierarchy (FHC or PRA)

CRITICAL:
1. Use the EXACT parameter names shown above. For update_hpl_formula, the parameter is "new_formula" NOT "formula".
2. When updating formulas, PRESERVE the complete equation including "Hypothetical P&L = " before the calculation. DO NOT extract only the right-hand side.

Respond ONLY with a valid JSON object in this exact format:
{{
  "tool": "tool_name",
  "arguments": {{"arg_name": "arg_value"}}
}}

Examples:
- For "Get all hierarchies": {{"tool": "get_all_hierarchies", "arguments": {{}}}}
- For "Calculate HPL for ACCT-001 with FHC": {{"tool": "calculate_hypothetical_pnl", "arguments": {{"account_number": "ACCT-001", "hierarchy": "FHC"}}}}
- For "Update PRA formula to 'Hypothetical P&L = Trading P&L + Dividend P&L'": {{"tool": "update_hpl_formula", "arguments": {{"hierarchy": "PRA", "new_formula": "Hypothetical P&L = Trading P&L + Dividend P&L"}}}}
"""

        llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)
        response = await llm.ainvoke([HumanMessage(content=tool_selection_prompt)])

        tool_executions = []
        errors = []
        result_data = None

        try:
            # Parse tool selection from response
            response_text = response.content

            # Extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                tool_data = json.loads(json_str)

                tool_name = tool_data.get('tool')
                tool_args = tool_data.get('arguments', {})

                # Log reasoning
                reasoning = create_reasoning_step(
                    step_type="tool_call",
                    content=f"Calling {tool_name} with args: {tool_args}",
                    metadata={"subtask_id": current_subtask.id, "tool": tool_name, "args": tool_args}
                )

                # Execute via MCP
                try:
                    result = await mcp_manager.call_tool(tool_name, tool_args)
                    result_data = result

                    # Track execution
                    execution = create_tool_execution(
                        tool_name=tool_name,
                        arguments=tool_args,
                        result=result,
                        subtask_id=current_subtask.id
                    )

                    tool_executions.append(execution)

                    # Store in intermediate results
                    state["intermediate_results"][current_subtask.id] = result

                    # Mark subtask as completed
                    current_subtask.status = "completed"
                    current_subtask.result = result

                except Exception as e:
                    error = {
                        "subtask_id": current_subtask.id,
                        "tool": tool_name,
                        "error": str(e),
                        "timestamp": execution.timestamp if 'execution' in locals() else ""
                    }
                    errors.append(error)
                    current_subtask.status = "failed"
                    current_subtask.error = str(e)

            else:
                # Could not parse tool selection
                error = {
                    "subtask_id": current_subtask.id,
                    "tool": "unknown",
                    "error": "Failed to parse tool selection from LLM response",
                    "timestamp": ""
                }
                errors.append(error)
                current_subtask.status = "failed"
                current_subtask.error = "Failed to parse tool selection"

        except Exception as e:
            error = {
                "subtask_id": current_subtask.id,
                "tool": "unknown",
                "error": str(e),
                "timestamp": ""
            }
            errors.append(error)
            current_subtask.status = "failed"
            current_subtask.error = str(e)

        # Determine next task
        next_task_id = None
        completed_tasks = state["completed_subtasks"] if current_subtask.status == "completed" else state["completed_subtasks"]

        if current_subtask.status == "completed":
            completed_tasks = completed_tasks + [current_subtask.id]

        # Find next pending task
        for st in state["subtasks"]:
            if st.status == "pending":
                next_task_id = st.id
                break

        return {
            "tool_executions": tool_executions,
            "reasoning_steps": [reasoning] if 'reasoning' in locals() else [],
            "errors": errors,
            "error_recovery_mode": len(errors) > 0,
            "iteration_count": state["iteration_count"] + 1,
            "current_task": next_task_id,
            "completed_subtasks": [current_subtask.id] if current_subtask.status == "completed" else [],
            "intermediate_results": state["intermediate_results"]
        }

    return execute_tools
