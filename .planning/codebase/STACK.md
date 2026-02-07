# Technology Stack

**Analysis Date:** 2026-02-07

## Languages

**Primary:**
- Python 3.12 - All source code and tests

**Secondary:**
- Not applicable

## Runtime

**Environment:**
- Python 3.12 (minimum required version)
- `.python-version` file specifies 3.12

**Package Manager:**
- uv (modern Python package manager)
- Lockfile: `uv.lock` present (192KB, comprehensive dependency tree)

## Frameworks

**Core:**
- fastmcp 3.0.0b1 - MCP server framework for tool definitions and lifecycle management
- Pydantic - Data validation and schema definition (via fastmcp dependency)

**Testing:**
- pytest >=8.0 - Test runner
- pytest-asyncio >=0.23 - Async test support

**Build/Dev:**
- hatchling - Build backend (PEP 517 compliant)
- uv 0.9.26 - Package management and environment isolation

## Key Dependencies

**Critical:**
- fastmcp 3.0.0b1 - Entire server built on this framework; provides MCP protocol implementation, tool decorators, context management, and server lifespan
- Pydantic - Model definitions for all data structures (TeamConfig, TaskFile, InboxMessage, etc.)

**Infrastructure:**
- fcntl - File locking for inbox and task concurrency safety (Linux/Unix only, part of Python stdlib)
- subprocess - Spawning Claude Code instances via tmux commands
- pathlib - File system operations under `~/.claude/`

## Configuration

**Environment:**
- No environment variables required for the server itself
- Server discovers Claude Code binary via PATH
- Spawned teammates receive environment variables: `CLAUDECODE=1`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

**Build:**
- `pyproject.toml` - Project metadata, dependencies, build config, pytest settings
- `uv.lock` - Locked dependency versions for reproducible installs

## Platform Requirements

**Development:**
- Python 3.12+
- tmux (required for spawning teammates)
- Claude Code CLI on PATH
- Unix-like OS (Linux/macOS) - uses `fcntl` for file locking

**Production:**
- Deployment target: MCP server (runs as subprocess via uvx)
- Installed via: `uvx --from git+https://github.com/cs50victor/claude-code-teams-mcp claude-teams`
- Storage: `~/.claude/teams/` and `~/.claude/tasks/` directories

---

*Stack analysis: 2026-02-07*
