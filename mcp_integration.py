"""
MCP Server Integration for LangChain
Connects to the finance MCP server and converts MCP tools to LangChain tools
"""

import asyncio
import json
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import tool


class MCPToolManager:
    """Manages connection to MCP server and converts MCP tools to LangChain tools"""

    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.session = None
        self.tools_list = []

    async def connect(self):
        """Connect to the MCP server"""
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "--with", "mcp[cli]", "mcp", "run", self.server_script_path],
            env=None
        )

        # Create stdio client context
        self.stdio_context = stdio_client(server_params)
        self.read, self.write = await self.stdio_context.__aenter__()

        # Create session context
        self.session_context = ClientSession(self.read, self.write)
        self.session = await self.session_context.__aenter__()

        # Initialize the connection
        await self.session.initialize()

        return self

    async def list_tools(self):
        """List all available tools from the MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")

        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a specific tool on the MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")

        result = await self.session.call_tool(tool_name, arguments)

        # Extract content from result
        if hasattr(result, 'content') and len(result.content) > 0:
            content_item = result.content[0]
            if hasattr(content_item, 'text'):
                return content_item.text

        return str(result)

    async def list_prompts(self):
        """List all available prompts from the MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")

        result = await self.session.list_prompts()
        return result.prompts

    async def get_prompt(self, name: str, arguments: dict = None):
        """Get a specific prompt from the MCP server

        Args:
            name: Name of the prompt to retrieve
            arguments: Optional dictionary of arguments for the prompt

        Returns:
            Prompt result with messages
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")

        result = await self.session.get_prompt(name, arguments or {})
        return result

    async def get_langchain_tools(self):
        """Convert MCP tools to LangChain tools"""
        tools = await self.list_tools()
        langchain_tools = []

        for mcp_tool in tools:
            # Create a LangChain tool for each MCP tool
            langchain_tool = self._create_langchain_tool(mcp_tool)
            langchain_tools.append(langchain_tool)

        return langchain_tools

    def _create_langchain_tool(self, mcp_tool):
        """Create a LangChain tool from an MCP tool"""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, create_model, Field
        from typing import Any, Dict

        tool_name = mcp_tool.name
        tool_description = mcp_tool.description or f"MCP tool: {tool_name}"

        # Get input schema from MCP tool
        input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}

        # Create Pydantic model from input schema if available
        if input_schema and 'properties' in input_schema:
            # Build fields for the Pydantic model
            fields = {}
            properties = input_schema.get('properties', {})
            required_fields = input_schema.get('required', [])

            for field_name, field_info in properties.items():
                field_type = str  # Default to str
                field_desc = field_info.get('description', '')

                # Add to fields dict
                if field_name in required_fields:
                    fields[field_name] = (field_type, Field(description=field_desc))
                else:
                    fields[field_name] = (field_type, Field(default=None, description=field_desc))

            # Create dynamic Pydantic model
            ArgsModel = create_model(f"{tool_name}Args", **fields)
        else:
            # No schema - use generic dict
            ArgsModel = None

        # Create async function for this specific tool
        async def tool_func(**kwargs) -> str:
            """Dynamically created tool that calls the MCP server"""
            result = await self.call_tool(tool_name, kwargs)
            return str(result)

        # Create structured tool
        if ArgsModel:
            return StructuredTool.from_function(
                coroutine=tool_func,
                name=tool_name,
                description=tool_description,
                args_schema=ArgsModel
            )
        else:
            return StructuredTool.from_function(
                coroutine=tool_func,
                name=tool_name,
                description=tool_description,
            )

    async def close(self):
        """Close the MCP connection"""
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
        if self.stdio_context:
            await self.stdio_context.__aexit__(None, None, None)


async def get_mcp_tools(server_path: str):
    """
    Connect to MCP server and return LangChain-compatible tools

    Args:
        server_path: Path to the MCP server script

    Returns:
        List of LangChain tools
    """
    manager = MCPToolManager(server_path)
    await manager.connect()

    # Get tools
    tools = await manager.get_langchain_tools()

    # Print available tools
    print(f"Connected to MCP server. Available tools: {[t.name for t in tools]}")

    return tools, manager


def get_tools_sync(server_path: str):
    """
    Synchronous wrapper to get MCP tools

    Args:
        server_path: Path to the MCP server script

    Returns:
        Tuple of (tools list, manager instance)
    """
    return asyncio.run(get_mcp_tools(server_path))
