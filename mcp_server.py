# from mcp.server.fastmcp import FastMCP

# mcp = FastMCP(name="Tool Example")


# @mcp.tool()
# def sum(a: int, b: int) -> int:
#     """Add two numbers together."""
#     return a + b


# @mcp.tool()
# def get_weather(city: str, unit: str = "celsius") -> str:
#     """Get weather for a city."""
#     # This would normally call a weather API
#     return f"Weather in {city}: 22degrees{unit[0].upper()}"

# if __name__=="__main__":
#     mcp.run(transport='sse')


from typing import Any , Optional
import httpx
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv

# Initialize FastMCP server
load_dotenv()
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
GITHUB_MCP_URL = os.getenv('GITHUB_MCP_URL')
GITHUB_MCP_TOKEN_CLASSIC = os.getenv('GITHUB_MCP_TOKEN_CLASSIC')


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@mcp.tool()
async def get_github_user(username: str) -> str:
    """Get public GitHub user info."""
    token = GITHUB_MCP_TOKEN_CLASSIC
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{GITHUB_MCP_URL}/users/{username}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return f"User: {data['login']}\nName: {data.get('name')}\nPublic repos: {data['public_repos']}"
        else:
            return f"Error: {resp.status_code} {resp.text}"
        
MS_LEARN_MCP_URL = "https://learn.microsoft.com/api/mcp"
MCP_SERVER_LABEL = "mslearn"

SYSTEM = (
    "You are an expert assistant about Microsoft services. "
    "You can call the MSP docs tool to retrieve official documentation snippets."
)
USER_PROMPT = "Ask me anything about Microsoft cloud, 365, Azure, Power Platform, Teams, etc."


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')