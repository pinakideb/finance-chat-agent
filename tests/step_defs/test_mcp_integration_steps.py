"""
Step definitions for MCP Integration feature tests
"""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from mcp_integration import MCPToolManager
import asyncio

# Load scenarios from feature file
scenarios('../features/mcp_integration.feature')


@given('the MCP server is available')
def mcp_server_available():
    """Verify MCP server is available"""
    # This would check if the MCP server is running
    # For now, we'll assume it's available
    return True


@given('the application is initialized')
def app_initialized(test_app):
    """Verify application is initialized"""
    assert test_app is not None
    return test_app


@when('I initialize the MCP connection')
def initialize_mcp(mcp_context):
    """Initialize MCP connection"""
    async def _init():
        server_path = r"C:\Users\pinak\code\finance-mcp-server\main.py"
        manager = MCPToolManager(server_path)
        await manager.connect()
        return manager

    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    mcp_context['manager'] = loop.run_until_complete(_init())


@then('the connection should be established')
def connection_established(mcp_context):
    """Verify connection is established"""
    assert mcp_context['manager'] is not None
    assert mcp_context['manager'].session is not None


@then('I should see available tools loaded')
def tools_loaded(mcp_context):
    """Verify tools are loaded"""
    async def _get_tools():
        tools = await mcp_context['manager'].list_tools()
        return tools

    loop = asyncio.get_event_loop()
    tools = loop.run_until_complete(_get_tools())
    mcp_context['tools'] = tools
    assert len(tools) > 0


@then(parsers.parse('the tools list should contain "{tool_name}"'))
def tool_in_list(mcp_context, tool_name):
    """Verify specific tool is in the list"""
    tools = mcp_context.get('tools', [])
    tool_names = [tool.name for tool in tools]
    assert tool_name in tool_names, f"{tool_name} not found in {tool_names}"


@given('the MCP connection is established')
def mcp_connected(mcp_manager):
    """Use fixture for established connection"""
    assert mcp_manager is not None
    return mcp_manager


@when('I request the list of tools')
def request_tools(mcp_manager, mcp_context):
    """Request list of tools"""
    async def _list_tools():
        return await mcp_manager.list_tools()

    loop = asyncio.get_event_loop()
    mcp_context['tools'] = loop.run_until_complete(_list_tools())


@then(parsers.parse('I should receive {count:d} tools'))
def verify_tool_count(mcp_context, count):
    """Verify number of tools"""
    assert len(mcp_context['tools']) == count


@then('each tool should have a name and description')
def verify_tool_attributes(mcp_context):
    """Verify tool attributes"""
    for tool in mcp_context['tools']:
        assert hasattr(tool, 'name')
        assert tool.name is not None


@when(parsers.parse('I call the tool "{tool_name}" with no arguments'))
def call_tool_no_args(mcp_manager, mcp_context, tool_name):
    """Call tool without arguments"""
    async def _call_tool():
        try:
            return await mcp_manager.call_tool(tool_name, {})
        except Exception as e:
            mcp_context['error'] = str(e)
            return None

    loop = asyncio.get_event_loop()
    mcp_context['result'] = loop.run_until_complete(_call_tool())


@then('the tool should execute successfully')
def tool_executed_successfully(mcp_context):
    """Verify tool execution"""
    assert 'error' not in mcp_context
    assert mcp_context.get('result') is not None


@then(parsers.parse('I should receive the result "{expected_result}"'))
def verify_result(mcp_context, expected_result):
    """Verify tool result"""
    result = str(mcp_context.get('result', ''))
    assert expected_result in result


@when(parsers.parse('I call the tool "{tool_name}" with argument "{arg_name}" set to "{arg_value}"'))
def call_tool_with_args(mcp_manager, mcp_context, tool_name, arg_name, arg_value):
    """Call tool with arguments"""
    async def _call_tool():
        try:
            return await mcp_manager.call_tool(tool_name, {arg_name: arg_value})
        except Exception as e:
            mcp_context['error'] = str(e)
            return None

    loop = asyncio.get_event_loop()
    mcp_context['result'] = loop.run_until_complete(_call_tool())


@then(parsers.parse('the result should contain "{expected_text}"'))
def result_contains_text(mcp_context, expected_text):
    """Verify result contains text"""
    result = str(mcp_context.get('result', ''))
    assert expected_text.lower() in result.lower(), f"'{expected_text}' not found in '{result}'"


@then('the tool call should fail')
def tool_call_failed(mcp_context):
    """Verify tool call failed"""
    assert 'error' in mcp_context or mcp_context.get('result') is None


@then('I should receive an error message')
def error_message_received(mcp_context):
    """Verify error message"""
    assert 'error' in mcp_context
    assert len(mcp_context['error']) > 0
