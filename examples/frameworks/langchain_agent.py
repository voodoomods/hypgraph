"""
LangChain: create_agent with the record's tools, through MultiServerMCPClient (langchain-mcp-adapters).

    pip install "hypgraph[mcp]" langchain langchain-mcp-adapters
    python langchain_agent.py                         # scripted model: offline, free
    pip install langchain-openai
    python langchain_agent.py --real --model gpt-4.1-mini
        # OPENAI_API_KEY; --model takes any "provider:model" string init_chat_model knows, e.g.
        # anthropic:claude-sonnet-4-5 (with langchain-anthropic installed)

The story is in _story.py. handle_tool_errors=True (the adapter's default, spelled out below) turns a refused write
into a ToolMessage the model reads, instead of an exception that ends the run. The tools come from one client session
held for the whole run: client.get_tools() on its own would start a server process for every tool call.

To build the graph yourself instead, see langgraph_agent.py.
"""
from __future__ import annotations

import asyncio
import sys

import _story as story
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph_agent import scripted_model          # the same scripted chat model the LangGraph example uses


async def main() -> int:
    a = story.args("LangChain agent on a HypGraph record over MCP.", "use a real model (init_chat_model)")
    command, args = story.server(a.db)
    client = MultiServerMCPClient({"hypgraph": {"transport": "stdio", "command": command, "args": args}})
    async with client.session("hypgraph") as session:                 # one server process for the whole run
        tools = await load_mcp_tools(session, handle_tool_errors=True)  # a refusal goes back to the model
        if a.real:
            model = a.model if ":" in a.model else f"openai:{a.model}"
        else:
            model = scripted_model()
        agent = create_agent(model, tools, system_prompt=story.INSTRUCTIONS)
        out = await agent.ainvoke({"messages": [{"role": "user", "content": story.TASK}]},
                                  {"recursion_limit": 20})
    return story.outcome(a.db, out["messages"][-1].content, a.real)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
