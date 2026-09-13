import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call_mcp_tool(
    tool_name: str,
    arguments: dict
):
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )

    async with stdio_client(
        server_params
    ) as (read, write):

        async with ClientSession(
            read,
            write
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments
            )

            # MCP returns a CallToolResult.
            # Extract the actual text payload.
            output = []

            for item in result.content:

                if hasattr(item, "text"):

                    text = item.text

                    try:
                        output.append(
                            json.loads(text)
                        )

                    except json.JSONDecodeError:
                        output.append(text)

            if len(output) == 1:
                return output[0]

            return output


def run_tool(
    tool_name: str,
    arguments: dict
):
    return asyncio.run(
        call_mcp_tool(
            tool_name,
            arguments
        )
    )