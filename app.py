"""
Flask web application for Finance MCP Chat Agent
"""
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import asyncio
import json
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from mcp_integration import MCPToolManager
from agent.agent import FinanceAgent
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
        mcp_server_url = "http://localhost:8000/sse"
        mcp_manager = MCPToolManager(mcp_server_url)
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


@app.route('/api/test', methods=['GET', 'POST'])
def test_route():
    """Simple test route"""
    return jsonify({'status': 'ok', 'message': 'Test route works!'})


@app.route('/api/test-agent', methods=['GET'])
def test_agent():
    """Test agent initialization"""
    try:
        import traceback
        async def test_init():
            await initialize_mcp()
            mcp_server_url = "http://localhost:8000/sse"
            agent = FinanceAgent(mcp_server_url)
            await agent.initialize()
            return "Agent initialized successfully"

        result = run_async(test_init())
        return jsonify({'success': True, 'message': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/agent-chat', methods=['POST'])
def agent_chat():
    """Streaming endpoint for LangGraph agent with Server-Sent Events"""
    print("[AGENT-CHAT] Request received")
    data = request.json
    message = data.get('message')
    print(f"[AGENT-CHAT] Message: {message}")

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    def generate():
        print("[AGENT-CHAT] Starting generator")
        """Generator for SSE streaming"""
        async def stream_agent_response():
            print("[AGENT-CHAT] Initializing MCP...")
            await initialize_mcp()
            print("[AGENT-CHAT] MCP initialized")

            # Create agent instance
            mcp_server_url = "http://localhost:8000/sse"
            print(f"[AGENT-CHAT] Creating agent with MCP URL: {mcp_server_url}")
            agent = FinanceAgent(mcp_server_url)
            print("[AGENT-CHAT] Agent created, initializing...")
            await agent.initialize()
            print("[AGENT-CHAT] Agent initialized, starting run...")

            try:
                # Stream execution
                print(f"[AGENT-CHAT] Running agent with query: {message}")
                async for event in agent.run(message):
                    print(f"[AGENT-CHAT] Received event: {list(event.keys())}")
                    # event is a dict like {"node_name": state_update}
                    for node_name, state_update in event.items():
                        # Extract and stream different event types

                        # Reasoning steps
                        if "reasoning_steps" in state_update and state_update["reasoning_steps"]:
                            latest_reasoning = state_update["reasoning_steps"][-1]
                            print(f"[AGENT-CHAT] Sending reasoning step: {latest_reasoning.step_type}")
                            sse_data = {
                                "event_type": "reasoning",
                                "data": {
                                    "step_type": latest_reasoning.step_type,
                                    "content": latest_reasoning.content,
                                    "timestamp": latest_reasoning.timestamp,
                                    "metadata": latest_reasoning.metadata
                                },
                                "state_snapshot": {
                                    "iteration_count": state_update.get("iteration_count", 0),
                                    "completed_subtasks": len(state_update.get("completed_subtasks", [])),
                                    "total_subtasks": len(state_update.get("subtasks", []))
                                }
                            }
                            yield f"data: {json.dumps(sse_data)}\n\n"

                        # Subtask updates
                        if "subtasks" in state_update and state_update["subtasks"]:
                            for subtask in state_update["subtasks"]:
                                sse_data = {
                                    "event_type": "subtask_update",
                                    "data": {
                                        "id": subtask.id,
                                        "description": subtask.description,
                                        "status": subtask.status,
                                        "assigned_tools": subtask.assigned_tools,
                                        "result": subtask.result,
                                        "error": subtask.error
                                    }
                                }
                                yield f"data: {json.dumps(sse_data)}\n\n"

                        # Tool executions
                        if "tool_executions" in state_update and state_update["tool_executions"]:
                            latest_exec = state_update["tool_executions"][-1]
                            sse_data = {
                                "event_type": "tool_execution",
                                "data": {
                                    "tool_name": latest_exec.tool_name,
                                    "arguments": latest_exec.arguments,
                                    "result": latest_exec.result,
                                    "error": latest_exec.error,
                                    "timestamp": latest_exec.timestamp,
                                    "subtask_id": latest_exec.subtask_id
                                }
                            }
                            yield f"data: {json.dumps(sse_data)}\n\n"

                        # Final answer
                        if state_update.get("final_answer"):
                            sse_data = {
                                "event_type": "final_answer",
                                "data": state_update["final_answer"]
                            }
                            yield f"data: {json.dumps(sse_data)}\n\n"

                # Send completion event
                yield f"data: {json.dumps({'event_type': 'done'})}\n\n"

            finally:
                try:
                    await agent.close()
                except Exception as e:
                    # Ignore cleanup errors (async context scope issues)
                    print(f"[AGENT-CHAT] Cleanup warning (non-critical): {e}")

        # Run the async generator in the event loop
        loop = get_event_loop()
        async_gen = stream_agent_response()

        try:
            while True:
                future = asyncio.run_coroutine_threadsafe(async_gen.__anext__(), loop)
                yield future.result(timeout=120)
        except StopAsyncIteration:
            pass
        except Exception as e:
            print(f"Error in agent stream: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'event_type': 'error', 'data': str(e)})}\n\n"

    try:
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    except Exception as e:
        import traceback
        sys.stderr.write(f"\n\n[AGENT-CHAT] Fatal error before streaming started:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


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


@app.route('/api/mcp-status', methods=['GET'])
def mcp_status():
    """Check MCP connection status"""
    global mcp_manager

    if mcp_manager is None:
        return jsonify({
            'connected': False,
            'message': 'MCP not initialized'
        })

    return jsonify({
        'connected': True,
        'message': 'MCP server connected',
        'tools_count': len(tools) if tools else 0
    })


if __name__ == '__main__':
    print("Starting Finance MCP Chat Agent Web UI...")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
