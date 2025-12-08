"""
Execute the complete finance analysis workflow from MCP prompts
"""
import asyncio
import sys
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from mcp_integration import get_mcp_tools

load_dotenv()

# Set stdout encoding to UTF-8 to handle Unicode characters
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


async def run_complete_workflow():
    """Execute the complete finance analysis workflow using MCP prompts"""

    # Initialize LLM
    llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)

    # Connect to MCP server and get tools
    print("=" * 80)
    print("CONNECTING TO MCP SERVER")
    print("=" * 80)
    mcp_server_path = r"C:\Users\pinak\code\finance-mcp-server\main.py"
    tools, mcp_manager = await get_mcp_tools(mcp_server_path)

    try:
        # Bind tools to the LLM
        llm_with_tools = llm.bind_tools(tools)

        # Get the complete workflow prompt
        print("\n" + "=" * 80)
        print("LOADING COMPLETE WORKFLOW PROMPT")
        print("=" * 80)

        prompts = await mcp_manager.list_prompts()
        complete_prompt = None
        for prompt in prompts:
            if prompt.name == "finance_complete_analysis":
                complete_prompt = prompt
                break

        if not complete_prompt:
            print("Error: finance_complete_analysis prompt not found!")
            return

        # Get the prompt with FHC hierarchy
        prompt_result = await mcp_manager.get_prompt(
            "finance_complete_analysis",
            {"hierarchy": "FHC"}
        )

        print(f"[OK] Loaded workflow with {len(prompt_result.messages)} steps")

        # Convert MCP prompt messages to LangChain format
        conversation_messages = []
        for msg in prompt_result.messages:
            role = msg.role
            content = msg.content

            # Extract text content
            if hasattr(content, 'text'):
                text = content.text
            elif isinstance(content, list) and len(content) > 0:
                if hasattr(content[0], 'text'):
                    text = content[0].text
                else:
                    text = str(content[0])
            else:
                text = str(content)

            # Convert to LangChain message
            if role == "user":
                conversation_messages.append(HumanMessage(content=text))
            elif role == "assistant":
                conversation_messages.append(AIMessage(content=text))
            else:
                conversation_messages.append(SystemMessage(content=text))

        print("\n" + "=" * 80)
        print("WORKFLOW STEPS")
        print("=" * 80)
        for i, msg in enumerate(conversation_messages):
            print(f"\nStep {i+1}: {msg.content}")

        # Execute the workflow with multiple rounds
        print("\n" + "=" * 80)
        print("EXECUTING WORKFLOW")
        print("=" * 80)

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Round {iteration} ---")

            # Invoke LLM with current conversation
            response = await llm_with_tools.ainvoke(conversation_messages)

            # Check if there's text content to display
            if hasattr(response, 'content'):
                if isinstance(response.content, str):
                    print(f"\n[LLM Response]: {response.content}")
                elif isinstance(response.content, list):
                    for item in response.content:
                        if isinstance(item, dict) and 'text' in item:
                            print(f"\n[LLM Response]: {item['text']}")

            # Check for tool calls
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                # No more tool calls - workflow complete
                print("\n[OK] Workflow completed - no more tool calls needed")
                break

            # Execute tool calls
            print(f"\n[Executing {len(response.tool_calls)} tool call(s)]:")

            # Add the assistant's response to conversation
            conversation_messages.append(response)

            # Execute each tool and add results to conversation
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']

                print(f"  > {tool_name}({tool_args})")

                # Call the tool through MCP
                result = await mcp_manager.call_tool(tool_name, tool_args)
                print(f"    Result: {result[:200]}..." if len(str(result)) > 200 else f"    Result: {result}")

                # Add tool result to conversation
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id
                )
                conversation_messages.append(tool_message)

        if iteration >= max_iterations:
            print(f"\n[WARNING] Reached maximum iterations ({max_iterations})")

        # Get final summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)

        # Ask for final summary
        conversation_messages.append(HumanMessage(
            content="Please provide a comprehensive summary of the analysis."
        ))

        final_response = await llm_with_tools.ainvoke(conversation_messages)

        if hasattr(final_response, 'content'):
            if isinstance(final_response.content, str):
                print(f"\n{final_response.content}")
            elif isinstance(final_response.content, list):
                for item in final_response.content:
                    if isinstance(item, dict) and 'text' in item:
                        print(f"\n{item['text']}")

    finally:
        # Clean up MCP connection
        print("\n" + "=" * 80)
        print("CLOSING MCP CONNECTION")
        print("=" * 80)
        await mcp_manager.close()


if __name__ == "__main__":
    asyncio.run(run_complete_workflow())
