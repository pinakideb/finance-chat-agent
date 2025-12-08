# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangChain-based finance research agent that uses Claude Sonnet 4.5 with MCP (Model Context Protocol) server integration. The agent connects to a custom finance MCP server to access tools for HPL (Hypothetical P&L) calculations, account data, and hierarchy information.

## Setup and Environment

**Virtual Environment:**
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (Unix/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install mcp  # MCP SDK for server integration
```

**Environment Variables:**
- The project requires `ANTHROPIC_API_KEY` in `.env` file
- Optional: `OPENAPI_API_KEY` for OpenAI models
- API keys are loaded via `python-dotenv`
- Never commit the `.env` file to version control

**MCP Server Configuration:**
- MCP server configured in `.mcp.json`
- Finance MCP server location: `C:\Users\pinak\code\finance-mcp-server\main.py`
- Server runs via `uv` with stdio transport

## Running the Application

```bash
python main.py
```

The script connects to the MCP server, loads available tools, and executes test queries demonstrating:
- Listing available hierarchies
- Calculating hypothetical P&L for accounts

## Architecture

**Core Components:**

1. **MCP Integration (mcp_integration.py):**
   - `MCPToolManager`: Manages connection to MCP server via stdio
   - Converts MCP tools to LangChain-compatible `StructuredTool` instances
   - Automatically extracts input schemas from MCP tools to create Pydantic models
   - Handles async communication with MCP server

2. **Main Application (main.py):**
   - Async application using `asyncio.run(main())`
   - Connects to finance MCP server at startup
   - Binds MCP tools to Claude LLM using `.bind_tools()`
   - Creates chain: `prompt | llm_with_tools`
   - Executes tool calls through MCP manager

3. **Available MCP Tools:**
   - `get_hpl_formula(hierarchy)` - Get HPL formula for hierarchy (FHC, PRA)
   - `get_all_hierarchies()` - List all available hierarchies
   - `get_all_accounts()` - List all account numbers
   - `get_account_pnl(account_number)` - Get P&L components for account
   - `calculate_hypothetical_pnl(account_number, hierarchy)` - Calculate HPL

4. **Response Schema (main.py:13-17):**
   - `FinanceResponse` Pydantic model (currently unused in tool-based flow)
   - Fields: `topic`, `summary`, `sources`, `tools_used`
   - Can be used with `with_structured_output()` for final responses

**Data Flow:**

1. User query → LangChain prompt template
2. LLM determines which MCP tools to call
3. Tool calls sent to MCP server via stdio
4. MCP server executes tools and returns results
5. Results displayed to user

**Integration Points:**

- `.mcp.json` defines MCP server configuration
- `mcp_integration.py` handles MCP ↔ LangChain bridge
- Tool schemas automatically extracted from MCP server
- Add new MCP tools by modifying the finance-mcp-server

## Development Notes

**Adding MCP Tools:**
1. Add tool functions to `finance-mcp-server/main.py` using `@mcp.tool()` decorator
2. Tools are automatically discovered and converted to LangChain tools on connection
3. Input schemas are automatically extracted from MCP tool definitions
4. No changes needed in this repo - tools are dynamically loaded

**Adding Prompts from MCP:**
The MCP server also exposes prompts (`finance_step1`, `finance_complete_analysis`, etc.) that can be used for guided workflows. To use prompts:
1. Call `mcp_manager.session.list_prompts()` to get available prompts
2. Call `mcp_manager.session.get_prompt(name, arguments)` to retrieve prompt content
3. Integrate prompt messages into LangChain conversation flow

**Model Switching:**
Toggle between OpenAI and Anthropic by commenting/uncommenting lines 24-25 in main.py

**Testing Different Queries:**
Modify query strings in `main()` function (lines 52 and 74) to test different scenarios:
- "What hierarchies are available?"
- "Get P&L data for account ACCT-002"
- "Calculate HPL for account ACCT-003 with PRA hierarchy"

**Troubleshooting:**
- Ensure finance MCP server path in `.mcp.json` is correct
- Verify `uv` is installed and in PATH
- Check MCP server logs for tool execution errors
- Use `verbose=True` when creating chains for debugging
