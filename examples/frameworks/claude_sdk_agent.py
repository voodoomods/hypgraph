"""
Claude Agent SDK: Claude Code as the agent, with the record as its only tools (an MCP server it starts over stdio).

    pip install "hypgraph[mcp]" claude-agent-sdk
    python claude_sdk_agent.py                        # a real run: Claude Code signed in, or ANTHROPIC_API_KEY
    python claude_sdk_agent.py --model sonnet
    python claude_sdk_agent.py --check                # offline: the wiring only, no model

The story is in _story.py. Unlike the other examples there is no scripted model: the SDK drives Claude Code itself,
so a run is always a real one (a few cents on haiku). --check starts the record's server from the exact config the
SDK would use and confirms every tool the agent is allowed exists on it; CI runs that.

The options are the part to copy: the record as the only MCP server (strict_mcp_config ignores any you have
configured), no built-in tools (no shell, no file edits), and the record's tools pre-approved, so the agent can
read and write the record and do nothing else.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile

import _story as story
from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage, TextBlock,
                              ToolUseBlock, query)

TOOLS = ["overview", "find", "show", "add", "bound", "refusal_log"]


def options(db: str, model: str) -> ClaudeAgentOptions:
    command, args = story.server(db)
    return ClaudeAgentOptions(
        system_prompt=story.INSTRUCTIONS,
        mcp_servers={"hypgraph": {"type": "stdio", "command": command, "args": args}},
        strict_mcp_config=True,                                   # this server only
        tools=[],                                                 # no built-in tools
        allowed_tools=[f"mcp__hypgraph__{t}" for t in TOOLS],     # the record's, without a prompt
        model=model, max_turns=12, cwd=tempfile.gettempdir())


async def check(opts: ClaudeAgentOptions) -> int:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    cfg = opts.mcp_servers["hypgraph"]
    async with stdio_client(StdioServerParameters(command=cfg["command"], args=cfg["args"])) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
    allowed = [t.removeprefix("mcp__hypgraph__") for t in opts.allowed_tools]
    missing = [t for t in allowed if t not in names]
    print(f"the server answers with {len(names)} tools; the agent is allowed {', '.join(allowed)}")
    print("OK: every allowed tool exists." if not missing else f"Missing on the server: {', '.join(missing)}")
    return 1 if missing else 0


async def main() -> int:
    a = story.args("Claude Agent SDK agent on a HypGraph record over MCP.", model="haiku",
                   extra=lambda ap: ap.add_argument("--check", action="store_true",
                                                    help="offline: check the wiring, run no model"))
    opts = options(a.db, a.model)
    if a.check:
        return await check(opts)
    answer = ""
    try:
        async for msg in query(prompt=story.TASK, options=opts):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        print("tool:", block.name.removeprefix("mcp__hypgraph__"))
                    elif isinstance(block, TextBlock):
                        answer = block.text
            elif isinstance(msg, ResultMessage):
                answer = msg.result or answer
                print(f"done in {msg.num_turns} turns"
                      + (f", ${msg.total_cost_usd:.4f}" if msg.total_cost_usd else ""))
    except ClaudeSDKError as e:
        print(f"Claude Code didn't run: {e}")
        print("Sign it in (`claude`, then /login) or set ANTHROPIC_API_KEY. --check tests the wiring without a model.")
        return 2
    return story.outcome(a.db, answer, real=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
