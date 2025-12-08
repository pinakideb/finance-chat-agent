"""
Demonstration of using MCP prompts in LangChain workflow
Shows how to use the guided prompt chains from the finance MCP server
"""

import asyncio
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from mcp_integration import get_mcp_tools

load_dotenv()


async def list_available_prompts(mcp_manager):
    """List all available prompts from the MCP server"""
    print("\n=== Available MCP Prompts ===")
    prompts_result = await mcp_manager.session.list_prompts()

    for prompt in prompts_result.prompts:
        print(f"\n[Prompt]: {prompt.name}")
        if prompt.description:
            print(f"   Description: {prompt.description}")
        if hasattr(prompt, 'arguments') and prompt.arguments:
            args = [arg.name for arg in prompt.arguments]
            print(f"   Arguments: {', '.join(args)}")

    return prompts_result.prompts


async def get_prompt_content(mcp_manager, prompt_name, arguments=None):
    """Get the content of a specific prompt"""
    if arguments is None:
        arguments = {}

    prompt_result = await mcp_manager.session.get_prompt(prompt_name, arguments)
    return prompt_result


async def demo_single_step_prompts(mcp_manager, llm_with_tools):
    """Demonstrate using individual step prompts"""
    print("\n" + "="*80)
    print("DEMO 1: Using Individual Step Prompts")
    print("="*80)

    # Step 1: Get the first prompt
    print("\n[Step 1]: Getting initial prompt...")
    step1_result = await get_prompt_content(mcp_manager, "finance_step1")

    # Extract the prompt text
    step1_text = step1_result.messages[0].content.text if step1_result.messages else ""
    print(f"Prompt: {step1_text}")

    # User provides hierarchy
    hierarchy = "FHC"
    print(f"User response: {hierarchy}")

    # Step 2: Get formula prompt with hierarchy
    print("\n[Step 2]: Getting formula prompt...")
    step2_result = await get_prompt_content(mcp_manager, "finance_step2", {"hierarchy": hierarchy})
    step2_text = step2_result.messages[0].content.text if step2_result.messages else ""
    print(f"Prompt: {step2_text}")

    # Use LLM to execute this step
    response = await llm_with_tools.ainvoke([HumanMessage(content=step2_text)])
    print(f"LLM Response: {response.content}")

    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            result = await mcp_manager.call_tool(tool_call['name'], tool_call['args'])
            print(f"Tool Result: {result}")

    # Step 3: Get random account
    print("\n[Step 3]: Getting account selection prompt...")
    step3_result = await get_prompt_content(mcp_manager, "finance_step3", {"hierarchy": hierarchy})
    step3_text = step3_result.messages[0].content.text if step3_result.messages else ""
    print(f"Prompt: {step3_text}")

    # Simulate account selection
    account = "ACCT-001"
    print(f"Selected account: {account}")

    # Step 4: Calculate HPL
    print("\n[Step 4]: Getting calculation prompt...")
    step4_result = await get_prompt_content(mcp_manager, "finance_step4", {
        "hierarchy": hierarchy,
        "account_number": account
    })
    step4_text = step4_result.messages[0].content.text if step4_result.messages else ""
    print(f"Prompt: {step4_text}")

    response = await llm_with_tools.ainvoke([HumanMessage(content=step4_text)])

    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            result = await mcp_manager.call_tool(tool_call['name'], tool_call['args'])
            print(f"Calculation Result: {result}")


async def demo_complete_workflow_prompt(mcp_manager, llm_with_tools):
    """Demonstrate using the complete workflow prompt"""
    print("\n" + "="*80)
    print("DEMO 2: Using Complete Workflow Prompt")
    print("="*80)

    hierarchy = "FHC"

    # Get the complete workflow prompt
    print(f"\n[Complete Workflow]: Getting multi-step analysis for {hierarchy}...")
    workflow_result = await get_prompt_content(mcp_manager, "finance_complete_analysis", {
        "hierarchy": hierarchy
    })

    # The workflow prompt returns multiple messages
    print(f"\nWorkflow contains {len(workflow_result.messages)} steps:")

    for i, message in enumerate(workflow_result.messages, 1):
        step_text = message.content.text if hasattr(message.content, 'text') else str(message.content)
        print(f"\n--- Step {i} ---")
        print(f"Instruction: {step_text}")

        # Execute each step with the LLM
        response = await llm_with_tools.ainvoke([HumanMessage(content=step_text)])

        # Execute any tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                print(f"Calling tool: {tool_call['name']}")
                result = await mcp_manager.call_tool(tool_call['name'], tool_call['args'])
                print(f"Result: {result}")

        # If there's text content, print it
        if hasattr(response, 'content') and isinstance(response.content, str):
            print(f"LLM Response: {response.content}")


async def demo_integrated_conversation(mcp_manager, llm_with_tools):
    """Demonstrate integrating prompts into a conversational flow"""
    print("\n" + "="*80)
    print("DEMO 3: Integrated Conversational Flow with Prompts")
    print("="*80)

    # Build a conversation using prompts as guidance
    conversation_history = []

    # Start with system message
    system_msg = SystemMessage(content="""You are a financial analyst assistant.
    Follow the user's instructions to analyze hypothetical P&L data.""")
    conversation_history.append(system_msg)

    # Get step 1 prompt and add to conversation
    step1_result = await get_prompt_content(mcp_manager, "finance_step1")
    step1_text = step1_result.messages[0].content.text
    conversation_history.append(AIMessage(content=step1_text))

    # User responds
    user_choice = "PRA"
    conversation_history.append(HumanMessage(content=f"I want to analyze the {user_choice} hierarchy"))

    # Get step 2 prompt
    step2_result = await get_prompt_content(mcp_manager, "finance_step2", {"hierarchy": user_choice})
    step2_text = step2_result.messages[0].content.text
    conversation_history.append(HumanMessage(content=step2_text))

    # LLM processes the request
    print("\n[Conversational Flow]:")
    print(f"Assistant: {step1_text}")
    print(f"User: I want to analyze the {user_choice} hierarchy")
    print(f"System: {step2_text}")
    print("\nLLM processing...")

    response = await llm_with_tools.ainvoke(conversation_history)

    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"\nLLM decided to use {len(response.tool_calls)} tool(s):")
        for tool_call in response.tool_calls:
            print(f"  - {tool_call['name']}({tool_call['args']})")
            result = await mcp_manager.call_tool(tool_call['name'], tool_call['args'])
            print(f"    Result: {result}")


async def main():
    """Main function demonstrating MCP prompt usage"""

    # Initialize LLM
    llm = ChatAnthropic(model="claude-sonnet-4-5")

    # Connect to MCP server
    print("Connecting to MCP server...")
    mcp_server_path = r"C:\Users\pinak\code\finance-mcp-server\main.py"
    tools, mcp_manager = await get_mcp_tools(mcp_server_path)

    try:
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)

        # List available prompts
        await list_available_prompts(mcp_manager)

        # Run demos
        await demo_single_step_prompts(mcp_manager, llm_with_tools)
        await demo_complete_workflow_prompt(mcp_manager, llm_with_tools)
        await demo_integrated_conversation(mcp_manager, llm_with_tools)

        print("\n" + "="*80)
        print("All demos completed!")
        print("="*80)

    finally:
        print("\nClosing MCP connection...")
        await mcp_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
