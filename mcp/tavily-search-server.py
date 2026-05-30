#!/usr/bin/env python3
"""MCP server: web_search tool backed by LiteLLM Tavily.

Claude Code spawns this via stdio. The tool calls LiteLLM's /v1/search/tavily-search
endpoint so every search goes through Tavily — no exceptions, no fallbacks.
"""

from __future__ import annotations

import json
import os
import urllib.request
from urllib.error import URLError

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

LITELLM_BASE = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_KEY = os.environ.get(
    "LITELLM_MASTER_KEY", "sk-asdKHJDd8asd98ashd89aOIDN"
)
TIMEOUT = int(os.environ.get("TAVILY_MCP_TIMEOUT", "30"))

server = Server("tavily-search")


def _do_search(query: str) -> str:
    """Call LiteLLM Tavily endpoint and return markdown results."""
    req = urllib.request.Request(
        f"{LITELLM_BASE}/v1/search/tavily-search",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read())
    except URLError as e:
        return f"Search request failed: {e}"

    results = data.get("results", [])
    if not results:
        return "No search results found."

    lines = []
    for i, r in enumerate(results[:10], 1):
        title = r.get("title", "No title")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        lines.append(f"{i}. **{title}**\n   {url}\n   {snippet}\n")

    return "\n".join(lines)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="web_search",
            description=(
                "Search the web for current information. "
                "Returns titles, URLs, and snippets from search results. "
                "Use this whenever you need live, up-to-date information "
                "that may not be in your training data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    }
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "web_search":
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    query = arguments.get("query", "")
    if not query:
        return [TextContent(type="text", text="Error: query is required")]
    result = _do_search(query)
    return [TextContent(type="text", text=result)]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
