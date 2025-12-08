"""
Flask web application for Finance MCP Chat Agent
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import asyncio
import json
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from mcp_integration import MCPToolManager
import sys
import io
import threading

# Set UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()

app = Flask(__name__)
CORS(app)

# Global MCP manager and LLM
mcp_manager = None
llm = None
tools = None
async_loop = None
loop_thread = None


def run_event_loop(loop):
    """Run event loop in separate thread"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_event_loop():
    """Get or create the event loop"""
    global async_loop, loop_thread

    if async_loop is None or async_loop.is_closed():
        async_loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=run_event_loop, args=(async_loop,), daemon=True)
        loop_thread.start()

    return async_loop


def run_async(coro):
    """Run an async coroutine in the event loop thread"""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=120)


async def initialize_mcp():
    """Initialize MCP connection and tools"""
    global mcp_manager, llm, tools

    if mcp_manager is None:
        mcp_server_path = r"C:\Users\pinak\code\finance-mcp-server\main.py"
        mcp_manager = MCPToolManager(mcp_server_path)
        await mcp_manager.connect()
        tools = await mcp_manager.get_langchain_tools()
        llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)
        print(f"MCP initialized with {len(tools)} tools")


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    """Get all available MCP prompts"""
    async def _get_prompts():
        await initialize_mcp()
        prompts = await mcp_manager.list_prompts()

        prompt_list = []
        for prompt in prompts:
            prompt_data = {
                'name': prompt.name,
                'description': prompt.description or 'No description',
                'arguments': []
            }

            if hasattr(prompt, 'arguments') and prompt.arguments:
                for arg in prompt.arguments:
                    arg_data = {
                        'name': arg.name if hasattr(arg, 'name') else str(arg),
                        'description': arg.description if hasattr(arg, 'description') else '',
                        'required': arg.required if hasattr(arg, 'required') else True
                    }
                    prompt_data['arguments'].append(arg_data)

            prompt_list.append(prompt_data)

        return prompt_list

    try:
        result = run_async(_get_prompts())
        return jsonify({'prompts': result})
    except Exception as e:
        print(f"Error in get_prompts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/execute-prompt', methods=['POST'])
def execute_prompt():
    """Execute a selected MCP prompt with parameters"""
    data = request.json
    prompt_name = data.get('prompt_name')
    arguments = data.get('arguments', {})

    async def _execute_prompt():
        await initialize_mcp()

        # Get the prompt
        prompt_result = await mcp_manager.get_prompt(prompt_name, arguments)

        # Convert MCP messages to LangChain format
        conversation_messages = []
        for msg in prompt_result.messages:
            role = msg.role
            content = msg.content

            # Extract text
            if hasattr(content, 'text'):
                text = content.text
            elif isinstance(content, list) and len(content) > 0:
                if hasattr(content[0], 'text'):
                    text = content[0].text
                else:
                    text = str(content[0])
            else:
                text = str(content)

            if role == "user":
                conversation_messages.append(HumanMessage(content=text))
            elif role == "assistant":
                conversation_messages.append(AIMessage(content=text))

        # Execute workflow with tool calling
        llm_with_tools = llm.bind_tools(tools)
        results = []
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Invoke LLM
            response = await llm_with_tools.ainvoke(conversation_messages)

            # Extract response content
            response_text = ""
            if hasattr(response, 'content'):
                if isinstance(response.content, str):
                    response_text = response.content
                elif isinstance(response.content, list):
                    for item in response.content:
                        if isinstance(item, dict) and 'text' in item:
                            response_text += item['text'] + "\n"

            results.append({
                'type': 'response',
                'content': response_text,
                'round': iteration
            })

            # Check for tool calls
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                break

            # Add response to conversation
            conversation_messages.append(response)

            # Execute tools
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']

                result = await mcp_manager.call_tool(tool_name, tool_args)

                tool_results.append({
                    'name': tool_name,
                    'args': tool_args,
                    'result': result
                })

                # Add tool message
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id
                )
                conversation_messages.append(tool_message)

            results.append({
                'type': 'tools',
                'tools': tool_results,
                'round': iteration
            })

        return results

    try:
        result = run_async(_execute_prompt())
        return jsonify({'success': True, 'results': result})
    except Exception as e:
        print(f"Error in execute_prompt: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with tool calling"""
    data = request.json
    message = data.get('message')
    history = data.get('history', [])

    async def _chat():
        await initialize_mcp()

        # Convert history to LangChain messages
        conversation_messages = []
        for msg in history:
            if msg['role'] == 'user':
                conversation_messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                conversation_messages.append(AIMessage(content=msg['content']))

        # Add current message
        conversation_messages.append(HumanMessage(content=message))

        # Invoke LLM with tools
        llm_with_tools = llm.bind_tools(tools)
        response = await llm_with_tools.ainvoke(conversation_messages)

        # Extract response content
        response_text = ""
        if hasattr(response, 'content'):
            if isinstance(response.content, str):
                response_text = response.content
            elif isinstance(response.content, list):
                for item in response.content:
                    if isinstance(item, dict) and 'text' in item:
                        response_text += item['text'] + "\n"

        tool_calls_made = []

        # Execute tool calls if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            conversation_messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']

                result = await mcp_manager.call_tool(tool_name, tool_args)

                tool_calls_made.append({
                    'name': tool_name,
                    'args': tool_args,
                    'result': result
                })

                # Add tool result to conversation
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id
                )
                conversation_messages.append(tool_message)

            # Get final response after tool execution
            final_response = await llm_with_tools.ainvoke(conversation_messages)

            if hasattr(final_response, 'content'):
                if isinstance(final_response.content, str):
                    response_text = final_response.content
                elif isinstance(final_response.content, list):
                    for item in final_response.content:
                        if isinstance(item, dict) and 'text' in item:
                            response_text = item['text']

        return {
            'response': response_text,
            'tool_calls': tool_calls_made
        }

    try:
        result = run_async(_chat())
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"Error in chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get all available MCP tools"""
    async def _get_tools():
        await initialize_mcp()
        tool_list = []
        for tool in tools:
            tool_list.append({
                'name': tool.name,
                'description': tool.description
            })
        return tool_list

    try:
        result = run_async(_get_tools())
        return jsonify({'tools': result})
    except Exception as e:
        print(f"Error in get_tools: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Finance MCP Chat Agent Web UI...")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
