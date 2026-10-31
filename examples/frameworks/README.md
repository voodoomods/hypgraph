# HypGraph with agent frameworks

One story, told once per framework, so the difference between the files is only the wiring.

An eval harness has compared two models on the same 1,000 held-out questions: model A got 812 right, model B 800.
An agent, connected to the record over MCP as the author `analyst`, is asked whether A is more accurate. It writes
"significantly more accurate". The record refuses that with the arithmetic (p ≈ 0.5) and says what to write instead.
The agent writes the honest claim, and it is accepted. Afterwards the script reads the record in Python and prints
what was refused, what was accepted, and the refusal log.

The framework doesn't need to know HypGraph exists. It sees MCP tools, and the record does the checking.

| Framework | File | Install | MCP wiring |
|---|---|---|---|
| LangChain | [langchain_agent.py](langchain_agent.py) | `langchain langchain-mcp-adapters` | `MultiServerMCPClient` session → `create_agent` |
| LangGraph | [langgraph_agent.py](langgraph_agent.py) | `langgraph langchain-mcp-adapters` | `load_mcp_tools(session)` into a `ToolNode` |
| PydanticAI | [pydantic_ai_agent.py](pydantic_ai_agent.py) | `"pydantic-ai-slim[mcp]"` | `MCPToolset(StdioTransport(...))` |
| CrewAI | [crewai_agent.py](crewai_agent.py) | `crewai` | `Agent(mcps=[MCPServerStdio(...)])` |
| OpenAI Agents SDK | [openai_agents_sdk.py](openai_agents_sdk.py) | `openai-agents` | `Agent(mcp_servers=[MCPServerStdio(...)])` |
| Claude Agent SDK | [claude_sdk_agent.py](claude_sdk_agent.py) | `claude-agent-sdk` | `ClaudeAgentOptions(mcp_servers={...})` |

Every example also needs `pip install "hypgraph[mcp]"`. [_story.py](_story.py) holds what they share: the record
before the agent arrives, the task, the server command, and the check at the end.

## Run them

```bash
cd examples/frameworks
python langgraph_agent.py                          # scripted model: offline, free, the same every time
python langgraph_agent.py --real --model gpt-4.1-mini
```

With no flags, a scripted model plays a careful agent's moves through the framework's own tool-calling path:
read the overview, overclaim, read the refusal, write the honest claim. That shows the wiring works, including the
part that matters most, a refused write getting back to the model. It can't show a model reasoning. `--real` uses a
real model (`OPENAI_API_KEY`, or whatever the framework's model string needs; `--model` or `MODEL` picks it). A real
model passes if it got a claim accepted and fixed every refusal, because a careful model may write the honest claim
the first time.

`--db FILE` keeps the record, so you can open it afterwards with `hypgraph --db FILE serve`.

The Claude Agent SDK drives Claude Code itself and has no scripted mode. `python claude_sdk_agent.py` is a real run
(Claude Code signed in, or `ANTHROPIC_API_KEY`; `--model` takes `haiku`, `sonnet` or `opus`). `--check` starts the
record's server from the exact options the SDK would use and confirms every allowed tool exists. That needs no model.

## What to copy

- **One server per author.** `hypgraph --db FILE --as analyst mcp` writes as `analyst` and nothing else. The agent
  can't pass another name, and its verdicts count only if the investigation names it as a reviewer. Give each agent
  in a team its own server, with its own author.
- **Let a refusal reach the model.** A refused write is an MCP tool error whose text names the problem and the fix
  (for example `[SIGNIFICANCE_NOT_SHOWN]`). If the framework ends the run on a tool error, the agent never sees it:
  - LangChain: `load_mcp_tools(session, handle_tool_errors=True)`, the adapter's default, returns it as the tool's
    output, so `create_agent` needs nothing more. Hold one `client.session(...)` for the run: `client.get_tools()`
    alone starts a server process for every tool call.
  - LangGraph: `ToolNode(tools, handle_tool_errors=True)`.
  - PydanticAI: the default (`tool_error_behavior="retry"`) sends it back as a retry prompt. `max_retries` bounds it.
  - CrewAI and the OpenAI Agents SDK hand it back as the tool's output by default.
  - Claude Code shows tool errors to the model.
- **Keep the agent on the record.** The Claude example passes `tools=[]` (no shell, no file edits),
  `strict_mcp_config=True` (no other MCP servers) and pre-approves only the record's tools.
- **CrewAI names MCP tools after the command line** (`<command>_<args>_<tool>`, hashed past 64 characters). The
  example runs plain `hypgraph mcp` with `HYPGRAPH_DB` and `HYPGRAPH_AUTHOR` in its environment, so the tools come out
  as `hypgraph_mcp_add` and so on.

Frameworks that take plain Python functions as tools can skip MCP. Call `Graph` directly and return the refusal text
from `GraphError`; see [hypgraph.com/engineers](https://hypgraph.com/engineers/#connect).

Tested with langchain 1.4, langgraph 1.2, pydantic-ai 2.x, crewai 1.15, openai-agents 0.20 and claude-agent-sdk 0.2 (the scripted
runs, and the Claude `--check`, run in CI).
