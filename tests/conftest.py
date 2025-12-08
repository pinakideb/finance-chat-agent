"""
Pytest configuration and fixtures for BDD tests
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app as flask_app
from mcp_integration import MCPToolManager
from langchain_anthropic import ChatAnthropic


# Pytest-BDD configuration
def pytest_bdd_step_error(request, feature, scenario, step, step_func, step_func_args, exception):
    """Handle step errors"""
    print(f"\nStep failed: {step.name}")
    print(f"Exception: {exception}")


# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Context fixtures for storing test data
@pytest.fixture
def mcp_context():
    """Context for MCP-related test data"""
    return {}


@pytest.fixture
def api_context():
    """Context for API-related test data"""
    return {}


@pytest.fixture
def chat_context():
    """Context for chat-related test data"""
    return {}


@pytest.fixture
def prompt_context():
    """Context for prompt-related test data"""
    return {}


# Flask app fixture
@pytest.fixture
def test_app():
    """Create Flask test application"""
    flask_app.config['TESTING'] = True
    flask_app.config['DEBUG'] = False
    return flask_app


@pytest.fixture
def test_client(test_app):
    """Create Flask test client"""
    with test_app.test_client() as client:
        yield client


# MCP Manager fixture
@pytest.fixture(scope="session")
def mcp_manager(event_loop):
    """Create and initialize MCP manager"""
    async def _create_manager():
        server_path = r"C:\Users\pinak\code\finance-mcp-server\main.py"
        manager = MCPToolManager(server_path)
        try:
            await manager.connect()
            return manager
        except Exception as e:
            pytest.skip(f"Could not connect to MCP server: {e}")
            return None

    manager = event_loop.run_until_complete(_create_manager())

    yield manager

    # Cleanup
    if manager:
        try:
            event_loop.run_until_complete(manager.close())
        except:
            pass


@pytest.fixture
def mcp_tools(mcp_manager, event_loop):
    """Get MCP tools"""
    async def _get_tools():
        return await mcp_manager.get_langchain_tools()

    tools = event_loop.run_until_complete(_get_tools())
    return tools


@pytest.fixture
def llm():
    """Create LLM instance"""
    return ChatAnthropic(model="claude-sonnet-4-5", temperature=0)


@pytest.fixture
def llm_with_tools(llm, mcp_tools):
    """Create LLM with tools bound"""
    return llm.bind_tools(mcp_tools)


# Mock fixtures for testing without actual API calls
@pytest.fixture
def mock_mcp_manager(mocker):
    """Mock MCP manager for unit tests"""
    mock = mocker.Mock()
    mock.session = mocker.Mock()

    # Mock list_tools
    async def mock_list_tools():
        class MockTool:
            def __init__(self, name, desc):
                self.name = name
                self.description = desc

        return [
            MockTool("get_hpl_formula", "Get HPL formula"),
            MockTool("get_all_hierarchies", "Get hierarchies"),
            MockTool("get_all_accounts", "Get accounts"),
            MockTool("get_account_pnl", "Get account P&L"),
            MockTool("calculate_hypothetical_pnl", "Calculate HPL"),
        ]

    mock.list_tools = mock_list_tools

    # Mock call_tool
    async def mock_call_tool(tool_name, args):
        if tool_name == "get_all_hierarchies":
            return "FHC"
        elif tool_name == "get_hpl_formula":
            return "Hypothetical P&L = Trading P&L + Dividend P&L - Financing P&L"
        elif tool_name == "get_all_accounts":
            return "ACCT-001"
        elif tool_name == "calculate_hypothetical_pnl":
            return '{"hypothetical_pnl": 165000.0}'
        return "Mock result"

    mock.call_tool = mock_call_tool

    # Mock list_prompts
    async def mock_list_prompts():
        class MockPrompt:
            def __init__(self, name, desc, args=None):
                self.name = name
                self.description = desc
                self.arguments = args or []

        class MockArg:
            def __init__(self, name, required=True):
                self.name = name
                self.required = required
                self.description = None

        return [
            MockPrompt("finance_step1", "Step 1", []),
            MockPrompt("finance_step2", "Step 2", [MockArg("hierarchy")]),
            MockPrompt("finance_complete_analysis", "Complete workflow", [MockArg("hierarchy")]),
        ]

    mock.list_prompts = mock_list_prompts

    return mock


# Pytest markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


# Helpers
@pytest.fixture
def run_async(event_loop):
    """Helper to run async functions in tests"""
    def _run(coro):
        return event_loop.run_until_complete(coro)
    return _run
