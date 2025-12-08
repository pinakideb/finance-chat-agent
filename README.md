# Finance MCP Chat Agent

A web-based chat interface for financial analysis using LangChain, Claude Sonnet 4.5, and MCP (Model Context Protocol) server integration.

## Features

- **Prompt Selector**: Execute predefined MCP prompts with custom parameters
- **Chat Interface**: Interactive chat with AI assistant that uses MCP tools
- **MCP Integration**: Connects to finance MCP server for HPL calculations, account data, and hierarchy information
- **Multi-step Workflows**: Automated workflows with tool calling and result processing

## Prerequisites

- Python 3.10 or higher
- `uv` package manager ([installation instructions](https://github.com/astral-sh/uv))
- Anthropic API key (Claude)
- Finance MCP server running at `C:\Users\pinak\code\finance-mcp-server\main.py`

## Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd finance-chat-agent
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**:
   - Windows: `venv\Scripts\activate`
   - Unix/macOS: `source venv/bin/activate`

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your API keys:
     ```
     ANTHROPIC_API_KEY=your_actual_api_key_here
     ```

## Running the Application

### Web UI

Start the Flask web application:

```bash
python app.py
```

Access the application at: **http://localhost:5000**

### Command Line Workflows

Execute the complete workflow prompt:

```bash
python run_complete_workflow.py
```

Run the original demo:

```bash
python main.py
```

## Usage

### Prompt Selector (Web UI)

1. Select a prompt from the dropdown (e.g., `finance_complete_analysis`)
2. Fill in required parameters (e.g., hierarchy: "FHC")
3. Click "Execute Prompt"
4. View the multi-step workflow execution with tool calls and results

### Chat Interface (Web UI)

1. Type your question in the chat input
2. Press Enter or click Send
3. The AI will automatically use available MCP tools to answer your question
4. View tool usage and results in real-time

### Available MCP Tools

- `get_hpl_formula(hierarchy)` - Get HPL formula for hierarchy (FHC, PRA)
- `get_all_hierarchies()` - List all available hierarchies
- `get_all_accounts()` - List all account numbers
- `get_account_pnl(account_number)` - Get P&L components for account
- `calculate_hypothetical_pnl(account_number, hierarchy)` - Calculate HPL

### Available MCP Prompts

- `finance_step1` - Ask for hierarchy
- `finance_step2` - Ask for formula
- `finance_step3` - Get a random account
- `finance_step4` - Calculate Hypothetical P&L
- `finance_step5` - Summarize Hypothetical P&L
- `finance_complete_analysis` - Complete workflow (all steps)

## Project Structure

```
finance-chat-agent/
├── app.py                      # Flask web application
├── main.py                     # Original CLI demo
├── run_complete_workflow.py    # Complete workflow execution script
├── mcp_integration.py          # MCP server integration
├── templates/
│   └── index.html             # Web UI template
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## Security

**IMPORTANT**: Never commit your `.env` file to version control. It contains sensitive API keys.

- The `.gitignore` file is configured to exclude `.env` files
- Use `.env.example` as a template for setting up environment variables
- Always use environment variables for API keys and secrets

## MCP Server Configuration

The application connects to the finance MCP server specified in `.mcp.json`:

```json
{
  "mcpServers": {
    "finance-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--with", "mcp[cli]", "mcp", "run", "path/to/server"],
      "env": {}
    }
  }
}
```

## Development

### Running in Debug Mode

The Flask app runs in debug mode by default (set `debug=False` in production).

### Adding New MCP Tools

1. Add tool functions to the finance MCP server using `@mcp.tool()` decorator
2. Tools are automatically discovered and converted to LangChain tools
3. No changes needed in this repo - tools are dynamically loaded

## Troubleshooting

- **Event loop errors**: The app uses a persistent event loop in a separate thread. If you encounter errors, restart the application.
- **MCP server connection issues**: Verify the MCP server path in `app.py` and ensure `uv` is installed.
- **API rate limits**: Check your Anthropic API usage if requests fail.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
