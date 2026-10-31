"""
OpenAI Agents SDK: an Agent with the record as an MCP server (agents.mcp.MCPServerStdio).

    pip install "hypgraph[mcp]" openai-agents
    python openai_agents_sdk.py                       # scripted model (an agents Model): offline, free
    python openai_agents_sdk.py --real --model gpt-4.1-mini
        # OPENAI_API_KEY. For another provider, give the Agent an OpenAIChatCompletionsModel over its client.

The story is in _story.py. The SDK hands a refused write back to the model as the tool's output (its default
failure_error_function), so the next turn reads the refusal and writes again.
"""
from __future__ import annotations

import asyncio
import json
import sys

import _story as story
from agents import Agent, RunConfig, Runner
from agents.mcp import MCPServerStdio


def scripted_model():
    """An Agents SDK Model that plays the story's moves as Responses-API items."""
    from agents.items import ModelResponse
    from agents.models.interface import Model
    from agents.usage import Usage
    from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

    class Scripted(Model):
        async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                               tracing, **kw):
            items = input if isinstance(input, list) else []
            seen = [str(i.get("output", "")) for i in items if isinstance(i, dict)
                    and i.get("type") == "function_call_output"]
            move = story.next_move(seen)
            if isinstance(move, str):
                out = ResponseOutputMessage(id="msg", type="message", role="assistant", status="completed",
                                            content=[ResponseOutputText(type="output_text", text=move,
                                                                        annotations=[])])
            else:
                out = ResponseFunctionToolCall(id=f"fc-{len(seen)}", call_id=f"call-{len(seen)}",
                                               type="function_call", name=move[0], arguments=json.dumps(move[1]),
                                               status="completed")
            return ModelResponse(output=[out], usage=Usage(), response_id=None)

        def stream_response(self, *a, **kw):
            raise NotImplementedError("the scripted model doesn't stream")
    return Scripted()


async def main() -> int:
    a = story.args("OpenAI Agents SDK agent on a HypGraph record over MCP.", "use a real model (OpenAI)")
    command, args = story.server(a.db)
    async with MCPServerStdio(name="hypgraph", params={"command": command, "args": args},
                              cache_tools_list=True, client_session_timeout_seconds=30) as record:
        agent = Agent(name="analyst", instructions=story.INSTRUCTIONS, mcp_servers=[record],
                      model=a.model if a.real else scripted_model())
        result = await Runner.run(agent, story.TASK, max_turns=10,
                                  run_config=RunConfig(tracing_disabled=not a.real))
    return story.outcome(a.db, result.final_output, a.real)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
