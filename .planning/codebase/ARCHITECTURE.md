# Architecture

**Analysis Date:** 2026-02-07

## Pattern Overview

**Overall:** MCP Server with Domain-Driven Design

**Key Characteristics:**
- Single MCP server exposing team coordination primitives as tools
- Filesystem-based state persistence under `~/.claude/`
- Process orchestration via tmux for multi-agent spawning
- File locking for concurrent access safety
- Atomic writes for configuration updates

## Layers

**MCP Server Layer:**
- Purpose: Exposes team coordination as MCP tools
- Location: `src/claude_teams/server.py`
- Contains: FastMCP tool definitions, parameter validation, error handling
- Depends on: Domain layer (teams, tasks, messaging, spawner)
- Used by: MCP clients (Claude Code, OpenCode)

**Domain Layer:**
- Purpose: Core business logic for teams, tasks, and messaging
- Location: `src/claude_teams/teams.py`, `src/claude_teams/tasks.py`, `src/claude_teams/messaging.py`, `src/claude_teams/spawner.py`
- Contains: Team lifecycle, task management, inbox operations, teammate spawning
- Depends on: Models layer, filesystem
- Used by: MCP server layer

**Models Layer:**
- Purpose: Data structures and validation
- Location: `src/claude_teams/models.py`
- Contains: Pydantic models for teams, tasks, messages, results
- Depends on: Pydantic
- Used by: Domain layer, MCP server layer

**Persistence Layer:**
- Purpose: Filesystem-based storage
- Location: Embedded in domain modules
- Contains: JSON file I/O, file locking, atomic writes
- Depends on: `pathlib`, `fcntl`, `tempfile`
- Used by: Domain layer

## Data Flow

**Team Creation:**

1. MCP client calls `team_create` tool on `src/claude_teams/server.py`
2. Server validates team name, checks session state
3. `teams.create_team()` creates directories under `~/.claude/teams/<name>` and `~/.claude/tasks/<name>`
4. Writes `config.json` with lead member
5. Returns result to client

**State Management:**
- Teams: `~/.claude/teams/<team>/config.json` (atomic write via tempfile + os.replace)
- Tasks: `~/.claude/tasks/<team>/<id>.json` (file-locked writes)
- Messages: `~/.claude/teams/<team>/inboxes/<agent>.json` (fcntl-locked appends)

**Teammate Spawning:**

1. MCP client calls `spawn_teammate` tool
2. `spawner.spawn_teammate()` creates TeammateMember, adds to config
3. Creates inbox for teammate
4. Sends initial prompt as inbox message
5. Builds Claude Code command with agent flags
6. Executes `tmux split-window -dP` to spawn process
7. Captures pane ID, updates config with tmux reference
8. Returns spawn result

**Messaging Flow:**

1. Sender calls `send_message` tool with type and content
2. `messaging.send_plain_message()` or `messaging.send_structured_message()` creates InboxMessage
3. Acquires file lock on `~/.claude/teams/<team>/inboxes/.lock`
4. Appends message to recipient's inbox JSON
5. Releases lock
6. Recipient polls/reads inbox via `read_inbox` or `poll_inbox`

**Task Management:**

1. Lead creates task via `task_create` tool
2. `tasks.create_task()` assigns next ID, writes JSON
3. Lead assigns task via `task_update(owner="agent")`
4. `tasks.update_task()` validates, updates status, sends assignment notification
5. Teammate receives task via inbox, updates status as work progresses

## Key Abstractions

**TeamConfig:**
- Purpose: Represents team state and membership roster
- Examples: `src/claude_teams/models.py` lines 65-73
- Pattern: Pydantic model with discriminated union for lead vs teammate members

**MemberUnion:**
- Purpose: Type-safe representation of team lead vs teammates
- Examples: `src/claude_teams/models.py` lines 17-62
- Pattern: Tagged union with discriminator function

**InboxMessage:**
- Purpose: Unit of communication between agents
- Examples: `src/claude_teams/models.py` lines 90-98
- Pattern: Timestamped message with optional read tracking and color coding

**TaskFile:**
- Purpose: Persistent task state with dependency tracking
- Examples: `src/claude_teams/models.py` lines 76-87
- Pattern: Status machine with blocks/blockedBy for DAG dependencies

## Entry Points

**MCP Server:**
- Location: `src/claude_teams/server.py`
- Triggers: MCP client tool calls
- Responsibilities: Request handling, parameter validation, lifespan management

**Main Function:**
- Location: `src/claude_teams/server.py` line 389
- Triggers: `claude-teams` CLI command (pyproject.toml line 22)
- Responsibilities: Start FastMCP server

**Test Suite:**
- Location: `tests/test_*.py`
- Triggers: `pytest` command
- Responsibilities: Validate domain logic, concurrency safety

## Error Handling

**Strategy:** Fail-fast with explicit exceptions at domain boundaries

**Patterns:**
- Domain layer raises `ValueError` for business logic violations (invalid names, circular dependencies, status transitions)
- Domain layer raises `FileNotFoundError` for missing teams/tasks
- MCP server layer catches domain exceptions, wraps in `ToolError` for client
- File I/O failures propagate as OS exceptions

## Cross-Cutting Concerns

**Logging:** Not implemented - relies on MCP server framework logging

**Validation:** Pydantic models for data validation, regex validation for names (`_VALID_NAME_RE` in `src/claude_teams/teams.py` line 23)

**Authentication:** None - assumes trusted MCP client context

**Concurrency Safety:**
- Config updates: Atomic writes via `tempfile.mkstemp()` + `os.replace()` (`src/claude_teams/teams.py` lines 103-108)
- Inbox operations: `fcntl.flock()` file locking (`src/claude_teams/messaging.py` lines 27-34)
- Task operations: `fcntl.flock()` on `.lock` file per team (`src/claude_teams/tasks.py` lines 17-24)

---

*Architecture analysis: 2026-02-07*
