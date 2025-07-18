from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
        name="mcp_server",
        instructions="""
        This server provides tools for providing context for Figma designs.
        """,
        port=8000
    )
