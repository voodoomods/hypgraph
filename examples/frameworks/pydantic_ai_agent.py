"""
PydanticAI: an Agent with the record as an MCP toolset (MCPToolset, PydanticAI 2).

    pip install "hypgraph[mcp]" "pydantic-ai-slim[mcp]"
    python pydantic_ai_agent.py                       # scripted model (a FunctionModel): offline, free
    pip install "pydantic-ai-slim[openai]"
    python pydantic_ai_agent.py --real --model gpt-4.1-mini
        # OPENAI_API_KEY; or --model with any provider prefix PydanticAI knows, e.g. anthropic:claude-sonnet-4-5

The story is in _story.py. Here a refused write arrives as a retry: PydanticAI turns the MCP tool error into a
RetryPromptPart (tool_error_behavior="retry", the default), so the model reads the refusal and calls again.
max_retries bounds how many tries a tool gets in one run; include_instructions adds the server's own instructions
(how the record works, who you write as) to the agent's.
"""
from __future__ import annotations

import asyncio
import sys

import _story as story
from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset


def scripted_model():
    """A FunctionModel that plays the story's moves through PydanticAI's own tool-calling path."""
    from pydantic_ai.messages import ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
    from pydantic_ai.models.function import FunctionModel

    def script(messages, info):
        seen = [str(p.content) for m in messages for p in getattr(m, "parts", [])
                if isinstance(p, (ToolReturnPart, RetryPromptPart))]
        move = story.next_move(seen)
        if isinstance(move, str):
            return ModelResponse(parts=[TextPart(content=move)])
        return ModelResponse(parts=[ToolCallPart(tool_name=move[0], args=move[1])])
    return FunctionModel(script)


async def main() -> int:
    a = story.args("PydanticAI agent on a HypGraph record over MCP.", "use a real model")
    command, args = story.server(a.db)
    record = MCPToolset(StdioTransport(command, args), max_retries=3, include_instructions=True)
    model = (a.model if ":" in a.model else f"openai:{a.model}") if a.real else scripted_model()
    agent = Agent(model, toolsets=[record], instructions=story.INSTRUCTIONS)
    async with agent:                                          # one server process for the whole run
        result = await agent.run(story.TASK)
    return story.outcome(a.db, result.output, a.real)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
