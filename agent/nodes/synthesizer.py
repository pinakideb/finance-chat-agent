"""
Synthesizer Node: Aggregates all results into comprehensive final answer
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from agent.agent_state import AgentState, create_reasoning_step


async def synthesize_answer(state: AgentState) -> dict:
    """
    Synthesizes all subtask results into a coherent final answer
    Includes confidence levels and data sources
    """

    # Compile all results
    all_results = {}
    for subtask in state["subtasks"]:
        if subtask.status == "completed":
            all_results[subtask.id] = {
                "description": subtask.description,
                "result": state["intermediate_results"].get(subtask.id, subtask.result)
            }

    # Format results for synthesis
    results_text = ""
    for task_id, data in all_results.items():
        results_text += f"\n{task_id}: {data['description']}\nResult: {data['result']}\n"

    # Format tool executions
    tools_used = []
    for exec in state["tool_executions"]:
        tools_used.append({
            "tool": exec.tool_name,
            "args": exec.arguments,
            "result": exec.result[:200] if exec.result and len(str(exec.result)) > 200 else exec.result
        })

    # Format validation results
    validation_text = ""
    if state["validation_results"]:
        for val in state["validation_results"]:
            validation_text += f"\n- Confidence: {val.confidence:.2f}, Valid: {val.is_valid}"
            if val.issues:
                validation_text += f", Issues: {', '.join(val.issues)}"

    # Create synthesis prompt
    synthesis_prompt = f"""Synthesize a comprehensive answer to the user's query based on the workflow results.

Original query: {state['original_query']}

Completed subtasks and their results:
{results_text}

Tool executions performed:
{len(tools_used)} tool calls were made:
{chr(10).join([f"- {t['tool']}({t['args']}): {t['result']}" for t in tools_used])}

Validation results:
{validation_text if validation_text else "No validation was performed"}

Provide a comprehensive answer that:
1. Directly answers the original query
2. Integrates all relevant data points from the tool results
3. Notes any inconsistencies or validation concerns if present
4. Is clear and concise
5. Cites the specific tools/data sources used

Do not include any preamble or meta-commentary about the workflow - just provide the answer to the user's query.
"""

    llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0.3)
    response = await llm.ainvoke([HumanMessage(content=synthesis_prompt)])

    final_answer = response.content

    # Create reasoning step
    reasoning = create_reasoning_step(
        step_type="summary",
        content="Synthesized final answer from all subtask results",
        metadata={
            "subtasks_completed": len(all_results),
            "tools_used": list(set(e.tool_name for e in state["tool_executions"])),
            "total_tool_calls": len(state["tool_executions"])
        }
    )

    return {
        "final_answer": final_answer,
        "reasoning_steps": [reasoning],
        "should_continue": False,  # End graph execution
        "iteration_count": state["iteration_count"] + 1
    }
