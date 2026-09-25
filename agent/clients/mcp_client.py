import asyncio
from config import logger
from .django_client import fetch_agent_bootstrap_sync, parse_mcp_servers_from_bootstrap

def fetch_user_mcp_servers_sync(user_id: int, bootstrap: dict = None) -> list:
    """Fetch all active external MCP servers and cached tools for user via Django API."""
    if bootstrap is not None:
        return parse_mcp_servers_from_bootstrap(bootstrap)
    if not user_id:
        return []
    try:
        b = fetch_agent_bootstrap_sync(user_id)
        return parse_mcp_servers_from_bootstrap(b)
    except Exception as e:
        logger.error(f"Error fetching MCP servers for user {user_id}: {e}")
        return []

# Backwards compatibility alias
fetch_user_mcp_server_sync = fetch_user_mcp_servers_sync

async def execute_mcp_tool_call(server_url: str, auth_token: str, tool_name: str, arguments: dict) -> str:
    """Execute tool call on external MCP SSE server with strict timeout and fallback."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    logger.info(f"Connecting to MCP SSE at {server_url} to call '{tool_name}' with {arguments}")
    try:
        async def _call():
            async with sse_client(server_url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
                    out_texts = []
                    for c in result.content:
                        if hasattr(c, "text"):
                            out_texts.append(c.text)
                        else:
                            out_texts.append(str(c))
                    return "\n".join(out_texts) if out_texts else "{}"

        return await asyncio.wait_for(_call(), timeout=4.0)
    except asyncio.TimeoutError:
        logger.warning(f"MCP tool '{tool_name}' timed out after 4.0s")
        return "عذراً، استغرق نظام المتجر وقتاً أطول من المتوقع للرد."
    except Exception as ex:
        logger.error(f"Error calling MCP tool '{tool_name}' on {server_url}: {ex}", exc_info=True)
        return f"حدث خطأ أثناء الاتصال بنظام المتجر: {str(ex)}"
