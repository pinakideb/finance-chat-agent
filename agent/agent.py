"""
Main Finance Agent Class with LangGraph workflow
"""

from typing import Dict, Any, AsyncGenerator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from mcp_integration import MCPToolManager
from agent.agent_state import AgentState, create_initial_state
from agent.nodes.planner import plan_tasks
from agent.nodes.tool_caller import create_tool_caller
from agent.nodes.validator import create_validator
from agent.nodes.error_handler import handle_errors
from agent.nodes.synthesizer import synthesize_answer
from agent.routing import route_next_action


class FinanceAgent:
    """Main agent class that wraps LangGraph execution"""

    def __init__(self, mcp_server_path: str):
        self.mcp_server_path = mcp_server_path
        self.mcp_manager = None
        self.graph = None
        self.tools = None

    async def initialize(self):
        """Initialize MCP connection and build graph"""
        # Connect to MCP
        self.mcp_manager = MCPToolManager(self.mcp_server_path)
        await self.mcp_manager.connect()

        # Get available tools
        self.tools = await self.mcp_manager.get_langchain_tools()

        # Build LangGraph
        self.graph = self._build_graph()

        return self

    def _build_graph(self) -> StateGraph:
        """Constructs the LangGraph workflow"""

        # Create graph
        workflow = StateGraph(AgentState)

        # Create node functions with MCP manager in closure
        execute_tools_node = create_tool_caller(self.mcp_manager)
        validate_results_node = create_validator(self.mcp_manager)

        # Add nodes
        workflow.add_node("planner", plan_tasks)
        workflow.add_node("tool_caller", execute_tools_node)
        workflow.add_node("validator", validate_results_node)
        workflow.add_node("error_handler", handle_errors)
        workflow.add_node("synthesizer", synthesize_answer)

        # Set entry point
        workflow.set_entry_point("planner")

        # Add conditional edges from planner
        workflow.add_conditional_edges(
            "planner",
            route_next_action,
            {
                "tool_caller": "tool_caller",
                "synthesizer": "synthesizer"
            }
        )

        # Add conditional edges from tool_caller
        workflow.add_conditional_edges(
            "tool_caller",
            route_next_action,
            {
                "validator": "validator",
                "error_handler": "error_handler",
                "tool_caller": "tool_caller",  # Loop for next subtask
                "synthesizer": "synthesizer",
                "planner": "planner"  # For replanning
            }
        )

        # Add conditional edges from validator
        workflow.add_conditional_edges(
            "validator",
            route_next_action,
            {
                "tool_caller": "tool_caller",
                "synthesizer": "synthesizer"
            }
        )

        # Add conditional edges from error_handler
        workflow.add_conditional_edges(
            "error_handler",
            route_next_action,
            {
                "planner": "planner",  # Replan
                "tool_caller": "tool_caller",  # Retry
                "synthesizer": "synthesizer"  # Give up
            }
        )

        # Synthesizer always goes to END
        workflow.add_edge("synthesizer", END)

        # Compile with checkpointing
        memory = MemorySaver()

        return workflow.compile(checkpointer=memory)

    async def run(self, query: str, config: dict = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute the agent on a query and stream state updates

        Args:
            query: User query string
            config: Optional LangGraph config (for thread_id, etc.)

        Yields:
            State updates at each node execution
        """

        # Initialize state
        tool_names = [t.name for t in self.tools]
        initial_state = create_initial_state(
            query=query,
            available_tools=tool_names,
            max_iterations=15,
            max_retries=3
        )

        # Use default config if none provided
        if config is None:
            config = {"configurable": {"thread_id": "default"}}

        # Stream execution
        async for event in self.graph.astream(initial_state, config=config):
            # Each event is a dict with node name as key and updated state as value
            # Example: {"planner": {...updated_state...}}
            yield event

    async def close(self):
        """Close the MCP connection"""
        if self.mcp_manager:
            await self.mcp_manager.close()
