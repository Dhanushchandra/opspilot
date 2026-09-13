import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():

    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (
        read,
        write
    ):

        async with ClientSession(read, write) as session:

            await session.initialize()

            tools = await session.list_tools()

            print("\nAvailable MCP tools:\n")

            for tool in tools.tools:
                print(
                    f"- {tool.name}: "
                    f"{tool.description}"
                )

            print("\nTesting get_employee...\n")

            result = await session.call_tool(
                "get_employee",
                {
                    "employee_id": "emp_001"
                }
            )

            print(result)


if __name__ == "__main__":
    asyncio.run(main())