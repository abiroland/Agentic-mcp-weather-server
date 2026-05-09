import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

"""
Make sure:
1. The server is running before running this script.
2. The server is configured to use SSE transport.
3. The server is listening on port 8000
to run the server, use the command: `uv run mcpserver/server.py`
"""

async def main():
    async with sse_client("http://localhost:8000/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            tools_result = await session.list_tools()
            print("Available tools: ")
            for tool in tools_result.tools:
                print(f" - {tool.name}: {tool.description}")
            
            print("\nCalling get_weather_alerts tool for California (CA)...")
            result = await session.call_tool("get_weather_alerts", arguments={"state": "CA"})
            print(f"Result from get_weather_alerts: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())