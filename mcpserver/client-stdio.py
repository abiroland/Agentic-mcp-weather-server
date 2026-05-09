import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # define server parameters for stdio transport
    server_params = StdioServerParameters(
        command = "python",
        args = ["server.py"],
        env = None, # or specify environment variables as a dict
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
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