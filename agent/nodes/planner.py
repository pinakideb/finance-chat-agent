"""
Planner Node: Decomposes complex queries into actionable subtasks
"""

import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from agent.agent_state import AgentState, create_subtask, create_reasoning_step


async def plan_tasks(state: AgentState) -> dict:
    """
    Analyzes the query and creates a structured task plan
    Uses LLM to identify required tools and execution sequence
    """

    # Create planning prompt
    planning_prompt = f"""Analyze this financial query and break it down into specific subtasks.

Query: {state['original_query']}

Available tools:
{', '.join(state['available_tools'])}

Tool descriptions:
- get_hpl_formula(hierarchy): Get the HPL formula for a specific hierarchy (FHC or PRA)
- update_hpl_formula(hierarchy, new_formula): Update the formula for a hierarchy (use "new_formula" parameter). IMPORTANT: The formula must be the complete equation including "Hypothetical P&L = " followed by the calculation.
- get_all_hierarchies(): List all available hierarchies
- get_all_accounts(): List all account numbers
- get_account_pnl(account_number): Get P&L components for a specific account
- calculate_hypothetical_pnl(account_number, hierarchy): Calculate hypothetical P&L for an account using a hierarchy

Create a step-by-step plan. For each step:
1. Describe what needs to be done
2. Identify which tool(s) to use
3. Specify any dependencies on previous steps

IMPORTANT: Keep the plan simple and focused. For simple queries, create only 1-2 subtasks.
For complex queries involving multiple accounts or hierarchies, break into logical steps.

Respond ONLY with a valid JSON array in this exact format:
[
  {{
    "id": "task_1",
    "description": "Brief description of what to do",
    "tools": ["tool_name"]
  }},
  {{
    "id": "task_2",
    "description": "Another task",
    "tools": ["tool_name"]
  }}
]

Examples:
- Query "What hierarchies are available?" → [{{ "id": "task_1", "description": "Get all available hierarchies", "tools": ["get_all_hierarchies"] }}]
- Query "Calculate HPL for ACCT-001 with FHC" → [{{ "id": "task_1", "description": "Calculate HPL for ACCT-001 using FHC hierarchy", "tools": ["calculate_hypothetical_pnl"] }}]
"""

    # LLM call to generate plan
    llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)
    response = await llm.ainvoke([HumanMessage(content=planning_prompt)])

    # Parse subtasks from LLM response
    subtasks = []
    try:
        # Extract JSON from response
        response_text = response.content

        # Try to find JSON array in response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            tasks_data = json.loads(json_str)

            # Create SubTask objects
            for task_data in tasks_data:
                subtask = create_subtask(
                    task_id=task_data['id'],
                    description=task_data['description'],
                    assigned_tools=task_data.get('tools', [])
                )
                subtasks.append(subtask)
        else:
            # Fallback: create a single generic task
            subtasks = [
                create_subtask(
                    task_id="task_1",
                    description=f"Address query: {state['original_query']}",
                    assigned_tools=state['available_tools']
                )
            ]

    except Exception as e:
        # Fallback: create a single task if parsing fails
        print(f"Error parsing subtasks: {e}")
        subtasks = [
            create_subtask(
                task_id="task_1",
                description=f"Address query: {state['original_query']}",
                assigned_tools=state['available_tools']
            )
        ]

    # Add reasoning step for UI
    reasoning = create_reasoning_step(
        step_type="planning",
        content=f"Decomposed query into {len(subtasks)} subtask(s): " +
                ", ".join([st.description for st in subtasks]),
        metadata={"subtask_count": len(subtasks), "subtasks": [st.model_dump() for st in subtasks]}
    )

    # Determine if validation is needed (for HPL calculations)
    needs_validation = any(
        "calculate_hypothetical_pnl" in task.assigned_tools
        for task in subtasks
    )

    return {
        "subtasks": subtasks,
        "reasoning_steps": [reasoning],
        "current_task": subtasks[0].id if subtasks else None,
        "iteration_count": state["iteration_count"] + 1,
        "needs_replanning": False,
        "needs_validation": needs_validation
    }
