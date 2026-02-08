# OpenCode Teams MCP

## What This Is

An MCP server that enables multi-agent team coordination for OpenCode with Kimi K2.5. Agents spawn in tmux panes or as desktop apps, receive team identity via dynamically generated config files, and coordinate through shared task lists and inbox-based messaging.

## Core Value

Kimi K2.5 agents in OpenCode can coordinate as teams with shared task lists and messaging.

## Requirements

### Validated

- OpenCode binary discovery and version validation (>=1.1.52) -- v1.0
- Model translation to moonshot-ai/kimi-k2.5 format across 4 providers -- v1.0
- Dynamic agent config generation with team identity -- v1.0
- System prompt injection for inbox polling and task management -- v1.0
- MCP tool permissions set to "allow" for non-interactive mode -- v1.0
- Tmux pane spawning with timeout protection -- v1.0
- Desktop app spawning on Windows, macOS, Linux -- v1.0
- Dead/hung agent detection and force-kill -- v1.0
- Pre-built templates (researcher, implementer, reviewer, tester) -- v1.0
- Template customization per-spawn via custom_instructions -- v1.0
- All Claude Code-specific code removed -- v1.0
- Team lifecycle management (create, delete, read config) -- existing
- Task management with status tracking and dependencies -- existing
- Inbox-based messaging between agents -- existing
- Concurrency-safe operations (file locking, atomic writes) -- existing
- MCP server exposing all coordination primitives -- existing

### Active

(None - start fresh for v2.0 with /gsd:new-milestone)

### Out of Scope

- Claude Code backward compatibility -- full replacement, not hybrid
- Custom OpenCode fork -- use standard OpenCode CLI
- Alternative coordination systems (swarm-tools, etc.) -- keep existing protocol
- Windows native without WSL -- fcntl file locking is POSIX-only
- Recursive agent spawning -- known anti-pattern causing cascades

## Context

**Shipped v1.0** with 7,450 LOC Python across 8 phases (15 plans).

**Tech stack:** Python MCP server (FastMCP), YAML frontmatter config generation, tmux CLI spawning, desktop app subprocess spawning, file-based state persistence.

**Test coverage:** 330+ tests in pytest, all passing in WSL/Linux.

**Known tech debt:**
- Windows/fcntl: Tests require WSL/Linux (POSIX-only file locking)
- Human verification recommended: End-to-end health detection with real tmux panes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Replace Claude Code entirely (not hybrid) | User wants Kimi-only teams, simpler implementation | Good |
| Dynamic agent config generation | OpenCode agents need .md files for system prompts | Good |
| Keep existing storage layout | Preserve compatibility with team/task file structure | Good |
| Support both CLI and desktop spawning | User requested flexibility | Good |
| Tuple version comparison | Avoid packaging.version dependency | Good |
| All Claude aliases map to kimi-k2.5 | Single model architecture simplifies translation | Good |
| Credential references use {env:VAR_NAME} | Prevents secret leakage in config files | Good |
| Permission string "allow" not boolean | OpenCode non-interactive mode requires string shorthand | Good |
| claude-teams_* wildcard for MCP tools | Future-proof if new tools added | Good |
| Template lookup in server.py (MCP layer) | Keeps spawner generic, server handles resolution | Good |
| Desktop health check: alive/dead only | No content hash equivalent for desktop apps | Good |

## Constraints

- **Runtime:** OpenCode CLI must be on PATH (v1.1.52+)
- **Process:** Tmux for CLI spawning; desktop app for GUI spawning
- **Persistence:** ~/.opencode-teams/ storage layout maintained for compatibility
- **MCP:** Teammates must have opencode-teams MCP server configured
- **Model:** Default to Kimi K2.5 via moonshot-ai provider

---
*Last updated: 2026-02-08 after v1.0 milestone*
