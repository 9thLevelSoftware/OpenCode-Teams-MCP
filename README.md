<div align="center">

# opencode-teams

MCP server for orchestrating OpenCode agent teams.

</div>



https://github.com/user-attachments/assets/531ada0a-6c36-45cd-8144-a092bb9f9a19



## About

This MCP server implements a multi-agent coordination protocol for [OpenCode](https://opencode.ai). Multiple OpenCode instances coordinate as a team with shared task lists, inter-agent messaging, and tmux-based or desktop app spawning.

The protocol is exposed as a standalone [MCP](https://modelcontextprotocol.io/) server, making it available to any MCP client that speaks MCP. PRs are welcome.

## Install

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "opencode-teams": {
      "type": "local",
      "command": ["uvx", "--from", "git+https://github.com/DasBluEyedDevil/opencode-teams-mcp", "opencode-teams"],
      "enabled": true
    }
  }
}
```

Or for local development:

```json
{
  "mcp": {
    "opencode-teams": {
      "type": "local",
      "command": ["uv", "run", "opencode-teams"],
      "enabled": true
    }
  }
}
```

## Requirements

- Python 3.12+
- [tmux](https://github.com/tmux/tmux)
- [OpenCode](https://opencode.ai) CLI on PATH (v1.1.52+) or OpenCode Desktop app

## Tools

| Tool | Description |
|------|-------------|
| `team_create` | Create a new agent team. One team per server session. |
| `team_delete` | Delete a team and all its data. Fails if teammates are still active. |
| `spawn_teammate` | Spawn an OpenCode teammate in a tmux pane or desktop app instance. |
| `send_message` | Send direct messages, broadcasts, shutdown/plan approval responses. |
| `read_inbox` | Read messages from an agent's inbox. |
| `poll_inbox` | Long-poll an inbox for new messages (up to 30s). |
| `read_config` | Read team configuration and member list. |
| `task_create` | Create a new task with auto-incrementing ID. |
| `task_update` | Update task status, owner, dependencies, or metadata. |
| `task_list` | List all tasks for a team. |
| `task_get` | Get full details of a specific task. |
| `force_kill_teammate` | Forcibly kill a teammate's tmux pane or desktop process and clean up. |
| `list_agent_templates` | List available role templates (researcher, implementer, reviewer, tester). |
| `check_agent_health` | Check the health status (alive, dead, hung) of a single agent. |
| `check_all_agents_health` | Check the health status of all agents in the current team. |
| `process_shutdown_approved` | Remove a teammate after graceful shutdown approval. |

## How it works

- **Spawning**: Teammates launch as separate OpenCode processes in tmux panes or as desktop app instances. Each gets a unique agent ID (`name@team`) and color.
- **Messaging**: JSON-based inboxes under `~/.opencode-teams/teams/<team>/inboxes/`. File locking prevents corruption from concurrent reads/writes.
- **Tasks**: JSON task files under `~/.opencode-teams/tasks/<team>/`. Tasks have status tracking, ownership, and dependency management (`blocks`/`blockedBy`).
- **Concurrency safety**: Atomic writes via `tempfile` + `os.replace` for config. File locks for inbox operations.

## Window Management

When spawning agents with `backend='windows_terminal'` (Windows), you can control window behavior:

```python
# Window closes automatically when agent finishes (default)
spawn_teammate(
    team_name="my-team",
    name="worker-1",
    prompt="Do some work...",
    backend="windows_terminal",
    auto_close=True
)

# Window stays open for debugging (shows exit code, waits for key press)
spawn_teammate(
    team_name="my-team",
    name="worker-1",
    prompt="Do some work...",
    backend="windows_terminal",
    auto_close=False
)
```

**Note:** `auto_close` only affects Windows terminal backend. tmux panes are managed via `force_kill_teammate`, and desktop app windows must be closed manually.

## Storage layout

```
~/.opencode-teams/
├── teams/<team-name>/
│   ├── config.json          # team config + member list
│   └── inboxes/
│       ├── team-lead.json   # lead agent inbox
│       ├── worker-1.json    # teammate inboxes
│       └── .lock
└── tasks/<team-name>/
    ├── 1.json               # task files (auto-incrementing IDs)
    ├── 2.json
    └── .lock
```

## Model Compatibility

The following models have been tested and verified to work with `spawn_teammate`:

### OpenAI Models (OAuth Required)
**Working:**
- `openai/gpt-5.2` - General agentic model
- `openai/gpt-5.3-codex` - Most capable agentic coding model
- `openai/gpt-5.2-codex` - Advanced coding model
- `openai/gpt-5.1-codex` - Optimized for agentic coding

**Note:** Codex models require ChatGPT Plus/Pro subscription.

### Google Models
**Working:**
- `google/gemini-2.5-flash` - Fast, efficient (1M context)
- `google/gemini-2.5-pro` - Most capable Gemini model (1M context)
- `google/gemini-3-flash-preview` - Latest flash model
- `google/gemini-3-pro-preview` - Latest pro model

### Kimi for Coding Models
**Working:**
- `kimi-for-coding/k2p5` - Kimi K2.5 for coding tasks
- `kimi-for-coding/kimi-k2-thinking` - Kimi K2 with thinking capabilities

**Note:** These models work without special authentication beyond standard OpenCode setup.

### GitHub Copilot Models
**Working:**
- `github-copilot/gpt-5.2` - GPT 5.2 via Copilot
- `github-copilot/gpt-5.2-codex` - Codex via Copilot
- `github-copilot/claude-sonnet-4.5` - Claude Sonnet 4.5 via Copilot
- `github-copilot/claude-opus-4.5` - Claude Opus 4.5 via Copilot
- `github-copilot/gemini-2.5-pro` - Gemini 2.5 Pro via Copilot

**Note:** Requires GitHub Copilot subscription.

### Model Name Format
Always use the full `provider/model` format:
- ✅ `openai/gpt-5.2`
- ✅ `openai/gpt-5.3-codex`
- ✅ `google/gemini-2.5-flash`
- ✅ `kimi-for-coding/k2p5`
- ❌ `gpt-5.2` (missing provider prefix)

### Discovering Available Models
Use the `list_available_models()` tool to see which models are configured in your OpenCode setup:
```python
# List all available models
list_available_models()

# Filter by provider
list_available_models(provider="openai")
list_available_models(provider="google")

# Filter by reasoning effort
list_available_models(reasoning_effort="high")
```

This returns models from your `~/.config/opencode/opencode.json` configuration. If a model isn't listed there, it won't be available for spawning agents.

### Auto-Selection
Use `model="auto"` with `reasoning_effort` and `prefer_speed` to let the system select the best model:
```json
{
  "model": "auto",
  "reasoning_effort": "medium",
  "prefer_speed": false
}
```

### Quick Model Selection Guide

| Task Type | Recommended Model | Why |
|-----------|------------------|-----|
| **Fast tasks** | `google/gemini-2.5-flash` | Fastest response |
| **Complex coding** | `openai/gpt-5.3-codex` | Best coding + reasoning |
| **General coding** | `kimi-for-coding/k2p5` | No special auth needed |
| **Documentation** | `openai/gpt-5.2` | Strong writing capabilities |
| **Research** | `openai/gpt-5.1-codex-max` | Long-horizon analysis |
| **Budget option** | `github-copilot/gpt-5.2` | Included in Copilot |
| **No auth hassle** | `kimi-for-coding/k2p5` | Works out of the box |

See [MODELS.md](./MODELS.md) for detailed task-based recommendations.

## License

[MIT](./LICENSE)
