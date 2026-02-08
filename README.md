<div align="center">

# opencode-teams

MCP server for orchestrating OpenCode agent teams with Kimi K2.5.

</div>



https://github.com/user-attachments/assets/531ada0a-6c36-45cd-8144-a092bb9f9a19



## About

This MCP server implements a multi-agent coordination protocol for [OpenCode](https://opencode.ai) + Kimi K2.5. Multiple OpenCode instances coordinate as a team with shared task lists, inter-agent messaging, and tmux-based or desktop app spawning.

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

## License

[MIT](./LICENSE)
