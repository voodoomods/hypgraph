"""
LangGraph: a tool-calling graph whose tools are the record's, through MCP (langchain-mcp-adapters).

    pip install "hypgraph[mcp]" langgraph langchain-mcp-adapters
    python langgraph_agent.py                         # scripted model: offline, free
    pip install langchain-openai
    python langgraph_agent.py --real --model gpt-4.1-mini
        # OPENAI_API_KEY; OPENAI_BASE_URL for any other OpenAI-compatible provider

The story is in _story.py: the agent overclaims, the record refuses with the arithmetic, the agent writes the honest
claim. The one setting that matters here: a refused write reaches LangGraph as a tool error, and the ToolNode must
hand it back to the model (handle_tool_errors=True) instead of ending the run, so the model can read what to fix.
The same tools work in langchain's create_agent, which builds this graph for you.
"""
from __future__ import annotations

import asyncio
import sys

import _story as story
from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def scripted_model():
    """A LangChain chat model that plays the story's moves through LangChain's own tool-calling path."""
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage, ToolMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    class Scripted(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "scripted"

        def bind_tools(self, tools, **kw):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kw):
            move = story.next_move([str(m.content) for m in messages if isinstance(m, ToolMessage)])
            if isinstance(move, str):
                msg = AIMessage(content=move)
            else:
                msg = AIMessage(content="", tool_calls=[{"id": f"call-{len(messages)}", "name": move[0],
                                                         "args": move[1], "type": "tool_call"}])
            return ChatResult(generations=[ChatGeneration(message=msg)])
    return Scripted()


def build_graph(model, tools):
    llm = model.bind_tools(tools)

    async def agent(state: MessagesState):
        return {"messages": [await llm.ainvoke([SystemMessage(story.INSTRUCTIONS), *state["messages"]])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(tools, handle_tool_errors=True))   # a refusal goes back to the model
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)                # tool calls → tools, otherwise done
    g.add_edge("tools", "agent")
    return g.compile()


async def main() -> int:
    a = story.args("LangGraph agent on a HypGraph record over MCP.", "use a real model (langchain-openai)")
    command, args = story.server(a.db)
    async with stdio_client(StdioServerParameters(command=command, args=args)) as (read, write):
        async with ClientSession(read, write) as session:      # one server process for the whole run
            await session.initialize()
            tools = await load_mcp_tools(session)
            if a.real:
                from langchain_openai import ChatOpenAI
                model = ChatOpenAI(model=a.model)
            else:
                model = scripted_model()
            out = await build_graph(model, tools).ainvoke({"messages": [("user", story.TASK)]},
                                                          {"recursion_limit": 20})
    return story.outcome(a.db, out["messages"][-1].content, a.real)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
