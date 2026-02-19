<div align="center">

# OpenCode-Teams-MCP

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![OpenCode Compatible](https://img.shields.io/badge/OpenCode-Compatible-orange.svg)](https://opencode.ai)
[![Kimi K2.5](https://img.shields.io/badge/Kimi-K2.5-purple.svg)](https://kimi.moonshot.cn)

**MCP server for orchestrating OpenCode agent teams with Kimi K2.5**

[Installation](#install) • [Configuration](#configuration) • [Tools](#tools) • [Roadmap](#project-roadmap)

</div>

https://github.com/user-attachments/assets/531ada0a-6c36-45cd-8144-a092bb9f9a19

## About

OpenCode-Teams-MCP implements a **multi-agent coordination protocol** that transforms how AI agents collaborate on complex tasks. Built specifically for [OpenCode](https://opencode.ai) + Kimi K2.5, this MCP server enables multiple OpenCode instances to work together as a coordinated team.

### What You Get

- **Shared Task Management** — Auto-incrementing task IDs with status tracking, ownership, and dependency management
- **Inter-Agent Messaging** — Direct messages, broadcasts, and structured responses between teammates
- **Flexible Spawning** — Launch agents in tmux panes, tmux windows, or as desktop app instances
- **Health Monitoring** — Real-time agent status checks (alive, dead, hung) with automatic cleanup
- **Role-Based Templates** — Pre-configured agent roles (researcher, implementer, reviewer, tester)
- **Dynamic Model Discovery** — Automatic detection of available Kimi K2.5 models
- **Task Complexity Analysis** — Intelligent workload distribution based on task complexity

The protocol is exposed as a standalone [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server, making it available to any MCP client. PRs are welcome!

---

## Install

> ⚠️ **Production Use Warning**
> Pin to a release tag (e.g. `@v0.1.0`), not `main`. 
> There may be breaking changes between releases.

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "opencode-teams": {
      "type": "local",
      "command": ["uvx", "--from", "git+https://github.com/9thLevelSoftware/OpenCode-Teams-MCP@v0.1.0", "opencode-teams"],
      "enabled": true
    }
  }
}
```

---

## Requirements

- Python 3.12+
- [tmux](https://github.com/tmux/tmux) (for terminal-based spawning)
- [OpenCode](https://opencode.ai) CLI on PATH (v1.1.52+) **or** OpenCode Desktop app

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENCODE_TEAMS_BACKEND` | Backend to use (`opencode`, `claude`) | `opencode` |
| `OPENCODE_SERVER_URL` | OpenCode HTTP API URL | *(unset)* |
| `USE_TMUX_WINDOWS` | Spawn in tmux windows vs panes | *(unset)* |

Set these as environment variables before starting the MCP server:

```bash
export OPCODE_TEAMS_BACKEND=opencode
export USE_TMUX_WINDOWS=1  # Use windows instead of panes
```

---

## Client Configuration

### OpenCode (Recommended)

```json
{
  "mcp": {
    "opencode-teams": {
      "type": "local",
      "command": ["uvx", "--from", "git+https://github.com/9thLevelSoftware/OpenCode-Teams-MCP@v0.1.0", "opencode-teams"],
      "enabled": true
    }
  }
}
```

### Claude Code

```json
{
  "mcpServers": {
    "opencode-teams": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/9thLevelSoftware/OpenCode-Teams-MCP@v0.1.0", "opencode-teams"]
    }
  }
}
```

---

## Why OpenCode-Teams-MCP?

This project is a **significantly enhanced fork** of [cs50victor/claude-code-teams-mcp](https://github.com/cs50victor/claude-code-teams-mcp) with 86+ additional commits of improvements:

| Feature | claude-code-teams-mcp | OpenCode-Teams-MCP |
|---------|----------------------|-------------------|
| **Tools** | 11 | **15** (+4) |
| **LLM Optimization** | Claude Code | **Kimi K2.5** |
| **Task Complexity Analysis** | ❌ | ✅ |
| **Dynamic Model Discovery** | ❌ | ✅ |
| **Agent Templates** | Basic | **4 roles** (researcher, implementer, reviewer, tester) |
| **Windows Support** | Limited | **Enhanced** |
| **Health Monitoring** | Basic | **Advanced** (per-agent + all-agents checks) |
| **Graceful Shutdown** | ❌ | ✅ |

---

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

---

## How It Works

### Team Lifecycle

1. **Create Team** — Call `team_create` to initialize a new team session
2. **Spawn Teammates** — Use `spawn_teammate` with a role template to add agents
3. **Assign Tasks** — Create tasks with `task_create` and update with `task_update`
4. **Coordinate** — Agents communicate via `send_message` and `read_inbox`
5. **Monitor** — Use health check tools to ensure agents are responsive
6. **Cleanup** — Delete team with `team_delete` when done

### Agent Communication Flow

```
┌─────────────┐     send_message      ┌─────────────┐
│   Agent A   │ ────────────────────> │   Agent B   │
│  (Leader)   │                       │ (Teammate)  │
└─────────────┘                       └─────────────┘
       │                                     │
       │    poll_inbox / read_inbox          │
       │ <───────────────────────────────────│
       │                                     │
       │    task_update (status/progress)    │
       │ <───────────────────────────────────│
```

### Spawning Modes

| Mode | Use Case | Command |
|------|----------|---------|
| **tmux pane** (default) | Terminal-based, shared window | Built-in |
| **tmux window** | Separate terminal windows | Set `USE_TMUX_WINDOWS=1` |
| **Desktop app** | GUI-based workflow | Automatic fallback |

---

## Project Roadmap

See [`.planning/PROJECT.md`](.planning/PROJECT.md) for detailed roadmap, architecture decisions, and future enhancements.

Planned features include:
- [ ] Web dashboard for team visualization
- [ ] Persistent team state across restarts
- [ ] Integration with additional LLM providers
- [ ] Advanced task dependency graphs
- [ ] Team performance analytics

---

## Development

```bash
# Clone the repository
git clone https://github.com/9thLevelSoftware/OpenCode-Teams-MCP.git
cd OpenCode-Teams-MCP

# Install dependencies
uv sync

# Run tests
uv run pytest

# Start the server locally
uv run opencode-teams
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Forked from [cs50victor/claude-code-teams-mcp](https://github.com/cs50victor/claude-code-teams-mcp)
- Built for [OpenCode](https://opencode.ai) and [Kimi K2.5](https://kimi.moonshot.cn)
- Uses the [Model Context Protocol](https://modelcontextprotocol.io/)

---

<div align="center">

**[⬆ Back to Top](#opencode-teams-mcp)**

Made with ❤️ by 9th Level Software

</div>
