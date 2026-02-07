# Codebase Structure

**Analysis Date:** 2026-02-07

## Directory Layout

```
claude-code-teams-mcp/
├── .github/                # CI/CD workflows
│   ├── assets/            # Media assets
│   └── workflows/         # GitHub Actions
├── .planning/             # GSD planning directory
│   └── codebase/          # Codebase analysis documents
├── src/                   # Source code
│   └── claude_teams/      # Main package
├── tests/                 # Test suite
├── pyproject.toml         # Package configuration
├── uv.lock                # Dependency lock file
├── README.md              # Documentation
├── LICENSE                # MIT license
└── stress_test_lifecycle.py  # Standalone stress test
```

## Directory Purposes

**src/claude_teams/:**
- Purpose: Main package implementing MCP server and team coordination
- Contains: Server, domain logic, models
- Key files: `server.py`, `teams.py`, `tasks.py`, `messaging.py`, `spawner.py`, `models.py`

**tests/:**
- Purpose: Pytest test suite
- Contains: Unit and integration tests
- Key files: `conftest.py` (fixtures), `test_*.py` (test modules)

**.github/workflows/:**
- Purpose: CI/CD automation
- Contains: GitHub Actions workflows
- Key files: `ci.yml`

**.planning/codebase/:**
- Purpose: GSD-generated codebase analysis
- Contains: Architecture and structure documentation
- Key files: `ARCHITECTURE.md`, `STRUCTURE.md`

**.venv/:**
- Purpose: Python virtual environment
- Contains: Installed dependencies
- Generated: Yes
- Committed: No (in `.gitignore`)

## Key File Locations

**Entry Points:**
- `src/claude_teams/server.py`: MCP server implementation and main entry point
- `pyproject.toml`: Package metadata and CLI command registration

**Configuration:**
- `pyproject.toml`: Build system, dependencies, pytest config
- `.python-version`: Python version requirement (3.12+)
- `uv.lock`: Locked dependency versions

**Core Logic:**
- `src/claude_teams/server.py`: MCP tool definitions (394 lines)
- `src/claude_teams/teams.py`: Team lifecycle management (152 lines)
- `src/claude_teams/tasks.py`: Task CRUD and dependency management (338 lines)
- `src/claude_teams/messaging.py`: Inbox-based messaging (178 lines)
- `src/claude_teams/spawner.py`: Tmux-based teammate spawning (124 lines)
- `src/claude_teams/models.py`: Pydantic data models (167 lines)

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures (`tmp_claude_dir`)
- `tests/test_teams.py`: Team lifecycle tests (200 lines)
- `tests/test_tasks.py`: Task management tests
- `tests/test_messaging.py`: Messaging tests
- `tests/test_spawner.py`: Spawner tests
- `tests/test_server.py`: MCP server integration tests
- `tests/test_models.py`: Model validation tests
- `stress_test_lifecycle.py`: Manual stress test for edge cases (164 lines)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `messaging.py`, `spawner.py`)
- Test files: `test_<module>.py` (e.g., `test_teams.py`)
- Config files: `lowercase` or `.lowercase` (e.g., `pyproject.toml`, `.gitignore`)

**Directories:**
- Package directories: `snake_case` (e.g., `claude_teams`)
- Hidden directories: `.lowercase` (e.g., `.github`, `.planning`)

**Functions/Variables:**
- Functions: `snake_case` (e.g., `create_team`, `read_config`)
- Variables: `snake_case` (e.g., `team_name`, `agent_id`)
- Private functions: `_snake_case` (e.g., `_get_lifespan`, `_teams_dir`, `_would_create_cycle`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `TEAMS_DIR`, `TASKS_DIR`, `COLOR_PALETTE`)

**Classes:**
- Models: `PascalCase` (e.g., `TeamConfig`, `InboxMessage`, `TaskFile`)
- Exceptions: Standard Python exceptions (e.g., `ValueError`, `RuntimeError`)

## Where to Add New Code

**New MCP Tool:**
- Primary code: Add `@mcp.tool` decorated function in `src/claude_teams/server.py`
- Tests: Add tests in `tests/test_server.py`

**New Domain Function:**
- Team operations: `src/claude_teams/teams.py`
- Task operations: `src/claude_teams/tasks.py`
- Messaging operations: `src/claude_teams/messaging.py`
- Spawning operations: `src/claude_teams/spawner.py`
- Tests: Corresponding `tests/test_<module>.py`

**New Data Model:**
- Implementation: `src/claude_teams/models.py`
- Tests: `tests/test_models.py`

**New Message Type:**
- Model definition: Add Pydantic model to `src/claude_teams/models.py`
- Sending logic: Add helper function to `src/claude_teams/messaging.py`
- Server integration: Update `send_message` tool in `src/claude_teams/server.py`
- Tests: Add to `tests/test_messaging.py`

**Utilities:**
- Shared helpers: Add to relevant domain module (`teams.py`, `messaging.py`, etc.)
- Cross-cutting utilities: Create new module in `src/claude_teams/` if needed

## Special Directories

**~/.claude/teams/<team>/ (runtime):**
- Purpose: Team configuration and inboxes
- Generated: Yes (by `teams.create_team()`)
- Committed: No (user data directory)
- Structure: `config.json`, `inboxes/<agent>.json`, `inboxes/.lock`

**~/.claude/tasks/<team>/ (runtime):**
- Purpose: Task files with dependency tracking
- Generated: Yes (by `teams.create_team()`)
- Committed: No (user data directory)
- Structure: `<id>.json`, `.lock`

**.venv/:**
- Purpose: Python virtual environment
- Generated: Yes (by `uv` or `pip`)
- Committed: No (ignored via `.gitignore`)

**tests/__pycache__/ (build):**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No (ignored via `.gitignore`)

## Import Patterns

**Internal Imports:**
```python
from claude_teams import messaging, tasks, teams
from claude_teams.models import TeamConfig, InboxMessage, TaskFile
from claude_teams.spawner import spawn_teammate, kill_tmux_pane
```

**Third-party Imports:**
```python
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field
```

**Standard Library:**
```python
from pathlib import Path
from contextlib import contextmanager
import json
import fcntl
import tempfile
```

## Package Structure

**Package Name:** `claude-teams` (PyPI/distribution)

**Module Name:** `claude_teams` (import name)

**Entry Point:** `claude-teams` CLI command → `claude_teams.server:main`

**Build System:** Hatchling (PEP 517)

**Package Location:** `src/claude_teams/` (src layout)

**Wheel Contents:** `src/claude_teams` packaged as `claude_teams` module

---

*Structure analysis: 2026-02-07*
