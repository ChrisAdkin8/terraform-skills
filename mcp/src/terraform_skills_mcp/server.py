"""FastMCP server entrypoint — registers all four workflow tool modules."""

from __future__ import annotations

from fastmcp import FastMCP

from .tools import analyze, cost, refactor, test

mcp = FastMCP("terraform-skills")

analyze.register(mcp)
cost.register(mcp)
refactor.register(mcp)
test.register(mcp)


def main() -> None:
    """Console-script entrypoint: run the server on stdio (default MCP transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
