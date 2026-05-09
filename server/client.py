import asyncio
from langchain_anthropic import ChatAnthropic

from mcp_use import MCPAgent, MCPClient
from dotenv import load_dotenv
import os

load_dotenv()

async def run_memory_client():

    #load the Anthropic API key from environment variables
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    # configure file path
    config_path = "server/mcp.json"

    print("Initializing chat client...")

    # initialize the MCP client
    client = MCPClient.from_config_file(config_path)
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.7, anthropic_api_key=anthropic_api_key)

    #create an agent with memory enabled
    agent = MCPAgent(
        client=client, 
        llm=llm, 
        memory_enabled=True, 
        max_steps=15)
    
    print("\n=== Interactive MCP chat session ===")
    print("Type 'exit' to end the session.\n")
    print("Type clear to clear the conversation history\n")


    try:        
        while True:
            # Get user input
            user_input = input("\nYou: ")

            # Check for exit or clear commands
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting chat session.")
                break

            # Clear conversation history if user types "clear"
            elif user_input.lower() == "clear":
                agent.clear_conversation_history()
                print("Conversation history cleared.")
                continue
            
            # Get agent response
            try:
                response = await agent.run(user_input)
                print(f"\nAgent: {response}\n")

            except Exception as e:
                print(f"Error occurred: {e}")
    
    finally:
        # ensure the client is properly closed
        if client and client.sessions:
            await client.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(run_memory_client())
