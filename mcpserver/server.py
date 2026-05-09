from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# initialize Fast
mcp = FastMCP(name="weather",
                host="0.0.0.0", #only used for SSE transport
                port=8000 #only used for SSE transport
        )

# constants 
NWS_API_AGENT = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


# make an nws request
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API and return the JSON response."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient(headers=headers) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            return None


# Return format 
def format_alert(feature: dict) -> str:
    """Format a weather alert feature into a readable string."""
    properties = feature["properties"]


    event = properties.get("event", "Unknown Event")
    severity = properties.get("severity", "Unknown Severity")
    description = properties.get("description", "No description available.")
    instructions = properties.get("instruction", "No instructions available.")
    
    return f"Alert: {event}\nSeverity: {severity}\nDescription: {description}\nInstructions: {instructions}"


@mcp.tool()
async def get_weather_alerts(state: str) -> str:
    """Get weather alerts for a given US state. Args state: Two-letter state code (e.g., 'CA' for California)."""
    url = f"{NWS_API_AGENT}/alerts/active?area={state}"
    data = await make_nws_request(url)
    
    if not data or "features" not in data:
        return "No alerts found or an error occurred."
    
    features = data["features"]
    if not features:
        return "No active alerts for this state."
    
    formatted_alerts = [format_alert(feature) for feature in features]
    return "\n\n".join(formatted_alerts)


# # Resource to get the upto news content of the weather impact on business
@mcp.tool()
async def get_latest_news_alerts() -> str:
    """ make a request to the news api to get the latest impact of weather alerts on business and return the content as a string."""
    url = "https://newsapi.org/v2/everything?q=weather+alerts+business&apiKey=YOUR_NEWS_API_KEY"
    data = await make_nws_request(url)
    if not data or "articles" not in data:
        return "No news articles found or an error occurred."
    articles = data["articles"]
    if not articles:
        return "No news articles found."
    formatted_articles = [f"Title: {article['title']}\nDescription: {article['description']}\nURL: {article['url']}" for article in articles]
    return "\n\n".join(formatted_articles)


# Resource endpoint for application settings
@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    """Echo the provided message."""
    return f"Resource echo: {message}"


def main():
    # initialize the server
    mcp.run()


if __name__ == "__main__":
    transport = "sse"
    if transport == "stdio":
        print(f"Starting MCP server with {transport} transport...")
        mcp.run(transport=transport)
    elif transport == "sse":
        print(f"Starting MCP server with {transport} transport...")
        mcp.run(transport=transport)
    else:
        raise ValueError(f"Unsupported transport: {transport}")