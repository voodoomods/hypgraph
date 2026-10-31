"""
CrewAI: a one-agent crew whose tools are the record's, through CrewAI's own MCP support (Agent(mcps=[...])).

    pip install "hypgraph[mcp]" crewai
    python crewai_agent.py                            # scripted model (a BaseLLM): offline, free
    python crewai_agent.py --real --model gpt-4.1-mini
        # OPENAI_API_KEY; any model id CrewAI's LLM accepts, e.g. anthropic/claude-sonnet-4-5

The story is in _story.py. CrewAI hands a refused write back to the agent as the tool's output, so the next step of
its tool loop reads the refusal and writes again. CrewAI names an MCP server's tools after its command line
(`<command>_<args>_<tool>`, hashed past 64 characters), so the server runs as plain `hypgraph mcp` with the record
and the author in its environment: the tools come out as hypgraph_mcp_add, hypgraph_mcp_overview, …
"""
from __future__ import annotations

import json
import sys

import _story as story
from crewai import Agent, Crew, Task
from crewai.mcp import MCPServerStdio


def scripted_llm():
    """A CrewAI BaseLLM that plays the story's moves as native tool calls."""
    from crewai.llm import BaseLLM

    class Scripted(BaseLLM):
        def __init__(self):
            super().__init__(model="scripted")

        def supports_function_calling(self) -> bool:
            return True

        def call(self, messages, tools=None, callbacks=None, available_functions=None, from_task=None,
                 from_agent=None, response_model=None):
            msgs = messages if isinstance(messages, list) else [{"role": "user", "content": str(messages)}]
            seen = [str(m.get("content", "")) for m in msgs if isinstance(m, dict) and m.get("role") == "tool"]
            move = story.next_move(seen)
            if isinstance(move, str):
                return move
            # CrewAI prefixes MCP tool names with the server's (hypgraph_mcp_add); call the one the story means
            names = [t.get("function", {}).get("name", "") for t in tools or []]
            name = next((n for n in names if n == move[0] or n.endswith("_" + move[0])), move[0])
            return [{"id": f"call-{len(seen)}", "type": "function",
                     "function": {"name": name, "arguments": json.dumps(move[1])}}]
    return Scripted()


def main() -> int:
    a = story.args("CrewAI crew on a HypGraph record over MCP.", "use a real model (CrewAI's LLM)")
    command, args, env = story.short_server(a.db)
    analyst = Agent(role="Analyst", goal="Record what the eval's counts support, and nothing more.",
                    backstory=story.INSTRUCTIONS, mcps=[MCPServerStdio(command=command, args=args, env=env)],
                    llm=a.model if a.real else scripted_llm(), max_iter=8, verbose=False)
    task = Task(description=story.TASK, expected_output="One sentence: what the record accepted.", agent=analyst)
    out = Crew(agents=[analyst], tasks=[task], verbose=False).kickoff()
    return story.outcome(a.db, out.raw, a.real)


if __name__ == "__main__":
    sys.exit(main())
