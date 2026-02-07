# External Integrations

**Analysis Date:** 2026-02-07

## APIs & External Services

**Claude Code CLI:**
- External dependency: Claude Code binary must be on PATH
  - SDK/Client: Invoked via `subprocess` in `src/claude_teams/spawner.py`
  - Discovery: `shutil.which("claude")` to find binary location
  - Auth: Handled by Claude Code itself (not managed by this server)

**MCP Protocol:**
- Protocol: Model Context Protocol
  - Implementation: fastmcp 3.0.0b1 library
  - Exposes 14 tools to MCP clients (Claude Code, OpenCode, etc.)

## Data Storage

**Databases:**
- None - all data stored as JSON files on local filesystem

**File Storage:**
- Local filesystem only
  - Team config: `~/.claude/teams/<team-name>/config.json`
  - Inboxes: `~/.claude/teams/<team-name>/inboxes/<agent-name>.json`
  - Tasks: `~/.claude/tasks/<team-name>/<task-id>.json`
  - Concurrency: `fcntl` file locks via `~/.claude/teams/<team-name>/inboxes/.lock` and `~/.claude/tasks/<team-name>/.lock`

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None - runs as local server
  - Team session tied to server lifespan (UUID generated per session)
  - Agent IDs: `{agent-name}@{team-name}` format
  - No authentication between agents or for tool calls

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Uses fastmcp's built-in logging
- tmux pane output for spawned teammates
- No structured logging framework

## CI/CD & Deployment

**Hosting:**
- Local execution only (MCP server runs on developer's machine)

**CI Pipeline:**
- GitHub Actions (`.github/workflows/ci.yml`)
  - Platform: ubuntu-latest
  - Steps: uv sync → pytest
  - Triggers: push to main, pull requests

## Environment Configuration

**Required env vars:**
- None required for the server
- Server sets for spawned teammates:
  - `CLAUDECODE=1` - Indicates Claude Code runtime
  - `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` - Enables agent teams feature

**Secrets location:**
- Not applicable (no secrets required)

## Webhooks & Callbacks

**Incoming:**
- None - MCP server responds to tool calls only

**Outgoing:**
- None - communication via JSON inbox files

## Process Management

**tmux Integration:**
- Tool: tmux (required external dependency)
  - Purpose: Spawn Claude Code teammates in separate panes
  - Commands used:
    - `tmux split-window -dP -F "#{pane_id}" <command>` - Spawn teammate in `src/claude_teams/spawner.py`
    - `tmux kill-pane -t <pane_id>` - Force kill teammate
  - Pane IDs stored in team config for lifecycle management

---

*Integration audit: 2026-02-07*
