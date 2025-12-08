import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from mcp_integration import get_mcp_tools

load_dotenv()  # Load environment variables from .env file


class FinanceResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]


async def main():
    """Main function to run the finance chat agent with MCP tools"""

    # Initialize LLM
    # llm = ChatOpenAI(model_name="gpt-4", temperature=0)
    llm = ChatAnthropic(model="claude-sonnet-4-5")

    # Connect to MCP server and get tools
    print("Connecting to MCP server...")
    mcp_server_path = r"C:\Users\pinak\code\finance-mcp-server\main.py"
    tools, mcp_manager = await get_mcp_tools(mcp_server_path)

    try:
        # Bind tools to the LLM
        llm_with_tools = llm.bind_tools(tools)

        # Create a prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a financial research assistant with access to tools for:
            - Getting HPL (Hypothetical P&L) formulas for hierarchies (FHC, PRA)
            - Getting all available hierarchies
            - Getting all account numbers
            - Getting account P&L data
            - Calculating hypothetical P&L for accounts

            Use these tools to answer user queries about financial data, P&L calculations, and account information.
            Be thorough and use the appropriate tools to gather the requested information.
            """),
            ("human", "{query}")
        ])

        # Test query - using MCP tools
        query = "What are all the available hierarchies?"
        print(f"\n[Query]: {query}\n")

        # Invoke with tools
        chain = prompt | llm_with_tools
        response = await chain.ainvoke({"query": query})

        print("[Response]:")
        print(response)

        # If there are tool calls, execute them
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"\n[Tool calls made]: {len(response.tool_calls)}")
            for tool_call in response.tool_calls:
                print(f"  - {tool_call['name']}({tool_call['args']})")
                # Execute the tool call through MCP
                result = await mcp_manager.call_tool(tool_call['name'], tool_call['args'])
                print(f"    Result: {result}")

        print("\n" + "="*80 + "\n")

        # Another test query - calculate HPL
        query2 = "Calculate the hypothetical P&L for account ACCT-001 using the FHC hierarchy"
        print(f"[Query]: {query2}\n")

        response2 = await chain.ainvoke({"query": query2})
        print("[Response]:")
        print(response2)

        if hasattr(response2, 'tool_calls') and response2.tool_calls:
            print(f"\n[Tool calls made]: {len(response2.tool_calls)}")
            for tool_call in response2.tool_calls:
                print(f"  - {tool_call['name']}({tool_call['args']})")
                result = await mcp_manager.call_tool(tool_call['name'], tool_call['args'])
                print(f"    Result: {result}")

        print("\n" + "="*80 + "\n")

        # Test MCP Prompts
        print("[Listing available MCP prompts]")
        prompts = await mcp_manager.list_prompts()
        if prompts:
            print(f"Found {len(prompts)} prompt(s):")
            for prompt in prompts:
                print(f"  - {prompt.name}: {prompt.description or 'No description'}")
                if hasattr(prompt, 'arguments') and prompt.arguments:
                    print(f"    Arguments: {list(prompt.arguments)}")
        else:
            print("No prompts available from MCP server.")

        print("\n" + "="*80 + "\n")

        # Test getting the complete workflow prompt
        if prompts and len(prompts) > 0:
            # Look for the finance_complete_analysis prompt
            complete_prompt = None
            for prompt in prompts:
                if prompt.name == "finance_complete_analysis":
                    complete_prompt = prompt
                    break

            # Fallback to first prompt if complete workflow not found
            if not complete_prompt:
                complete_prompt = prompts[0]

            prompt_name = complete_prompt.name
            print(f"[Getting prompt: {prompt_name}]")

            # Get the prompt - check if it requires arguments
            prompt_args = {}
            if hasattr(complete_prompt, 'arguments') and complete_prompt.arguments:
                # If prompt has arguments, provide sample values
                for arg in complete_prompt.arguments:
                    arg_name = arg.name if hasattr(arg, 'name') else str(arg)
                    # Provide sensible defaults based on argument name
                    if 'account' in arg_name.lower():
                        prompt_args[arg_name] = "ACCT-001"
                    elif 'hierarchy' in arg_name.lower():
                        prompt_args[arg_name] = "FHC"
                    else:
                        prompt_args[arg_name] = "sample_value"

            prompt_result = await mcp_manager.get_prompt(prompt_name, prompt_args)

            print(f"Prompt messages received: {len(prompt_result.messages)}")
            for i, msg in enumerate(prompt_result.messages):
                role = msg.role
                content = msg.content
                # Extract text from content
                if hasattr(content, 'text'):
                    text = content.text
                elif isinstance(content, list) and len(content) > 0:
                    if hasattr(content[0], 'text'):
                        text = content[0].text
                    else:
                        text = str(content[0])
                else:
                    text = str(content)

                print(f"\n  Message {i+1} [{role}]:")
                print(f"    {text[:200]}..." if len(text) > 200 else f"    {text}")

            print("\n" + "="*80 + "\n")

            # Demonstrate using prompt in LangChain conversation
            print(f"[Using prompt '{prompt_name}' in LangChain conversation]")

            # Convert MCP prompt messages to LangChain format
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

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

                # Convert to appropriate LangChain message type
                if role == "user":
                    conversation_messages.append(HumanMessage(content=text))
                elif role == "assistant":
                    conversation_messages.append(AIMessage(content=text))
                else:  # system or other
                    conversation_messages.append(SystemMessage(content=text))

            # Invoke LLM with the prompt messages
            response_from_prompt = await llm_with_tools.ainvoke(conversation_messages)
            print("[LLM Response using prompt]:")
            print(response_from_prompt.content if hasattr(response_from_prompt, 'content') else response_from_prompt)

            # Execute any tool calls from the prompt-based conversation
            if hasattr(response_from_prompt, 'tool_calls') and response_from_prompt.tool_calls:
                print(f"\n[Tool calls made from prompt]: {len(response_from_prompt.tool_calls)}")
                for tool_call in response_from_prompt.tool_calls:
                    print(f"  - {tool_call['name']}({tool_call['args']})")
                    result = await mcp_manager.call_tool(tool_call['name'], tool_call['args'])
                    print(f"    Result: {result}")

    finally:
        # Clean up MCP connection
        print("\nClosing MCP connection...")
        await mcp_manager.close()


if __name__ == "__main__":
    asyncio.run(main())

