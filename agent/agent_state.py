"""
State schema for LangGraph agentic workflow
Defines all state structures and supporting Pydantic models
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
import operator
from datetime import datetime


class SubTask(BaseModel):
    """Represents a decomposed subtask"""
    id: str
    description: str
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    assigned_tools: List[str] = []
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0


class ToolExecution(BaseModel):
    """Tracks a single tool execution"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    timestamp: str
    subtask_id: Optional[str] = None


class ReasoningStep(BaseModel):
    """Captures agent reasoning for UI display"""
    step_type: str  # 'planning', 'tool_call', 'validation', 'error', 'summary'
    content: str
    timestamp: str
    metadata: Dict[str, Any] = {}


class ValidationResult(BaseModel):
    """Result of cross-validation"""
    is_valid: bool
    confidence: float
    issues: List[str] = []
    cross_check_results: Dict[str, Any] = {}


class AgentState(TypedDict):
    """Main state for the LangGraph agent"""
    # Message history
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # Query tracking
    original_query: str
    current_task: Optional[str]

    # Task decomposition
    subtasks: List[SubTask]
    completed_subtasks: List[str]

    # Tool execution tracking
    tool_executions: Annotated[List[ToolExecution], operator.add]
    available_tools: List[str]

    # Reasoning and transparency
    reasoning_steps: Annotated[List[ReasoningStep], operator.add]

    # Iteration control
    iteration_count: int
    max_iterations: int

    # Validation and quality control
    validation_results: List[ValidationResult]
    needs_validation: bool

    # Error handling
    errors: Annotated[List[Dict[str, Any]], operator.add]
    retry_count: int
    max_retries: int

    # Results aggregation
    intermediate_results: Dict[str, Any]
    final_answer: Optional[str]

    # Control flags
    should_continue: bool
    needs_replanning: bool
    error_recovery_mode: bool


def get_timestamp() -> str:
    """Get current timestamp as ISO string"""
    return datetime.now().isoformat()


def create_reasoning_step(step_type: str, content: str, metadata: Dict[str, Any] = None) -> ReasoningStep:
    """Helper to create a reasoning step"""
    return ReasoningStep(
        step_type=step_type,
        content=content,
        timestamp=get_timestamp(),
        metadata=metadata or {}
    )


def create_tool_execution(
    tool_name: str,
    arguments: Dict[str, Any],
    result: Optional[str] = None,
    error: Optional[str] = None,
    subtask_id: Optional[str] = None
) -> ToolExecution:
    """Helper to create a tool execution record"""
    return ToolExecution(
        tool_name=tool_name,
        arguments=arguments,
        result=result,
        error=error,
        timestamp=get_timestamp(),
        subtask_id=subtask_id
    )


def create_subtask(task_id: str, description: str, assigned_tools: List[str]) -> SubTask:
    """Helper to create a subtask"""
    return SubTask(
        id=task_id,
        description=description,
        status="pending",
        assigned_tools=assigned_tools
    )


def create_initial_state(query: str, available_tools: List[str], max_iterations: int = 15, max_retries: int = 3) -> AgentState:
    """Create the initial state for a new agent run"""
    return {
        "messages": [],
        "original_query": query,
        "current_task": None,
        "subtasks": [],
        "completed_subtasks": [],
        "tool_executions": [],
        "available_tools": available_tools,
        "reasoning_steps": [],
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "validation_results": [],
        "needs_validation": False,
        "errors": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "intermediate_results": {},
        "final_answer": None,
        "should_continue": True,
        "needs_replanning": False,
        "error_recovery_mode": False
    }
