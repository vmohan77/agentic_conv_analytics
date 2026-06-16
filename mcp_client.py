from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client

# The MCP server must already be running on this URL before calling this function
MCP_SERVER_URL = "http://localhost:8000/sse"

@asynccontextmanager
async def get_mcp_session():
    # Opens the SSE connection and MCP session, keeps both alive for the caller
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session   # session is alive here; cleanup runs after caller exits

async def get_tools(session):
    tool_list = await session.list_tools()

    tools = []
    for tool in tool_list.tools:   # fixed: .tools not .tool
        tools.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
        )
    return tools

async def run_tools(tool_uses: list, session: ClientSession) -> list:
    tool_results = []

    for tool_use in tool_uses:
        print(f"Agent: Executing Tool {tool_use} \n")
        result = await session.call_tool(tool_use.name, tool_use.input)
        print(f"Agent: Got results from Tool {tool_use.name} successfully \n")
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": result.content[0].text if result.content else "Done",
        })

    #print(f"Tool results by calling MCP tools {tool_results} \n")
    return tool_results