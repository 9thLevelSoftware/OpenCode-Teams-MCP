# Coding Conventions

**Analysis Date:** 2026-02-07

## Naming Patterns

**Files:**
- Python modules: snake_case (e.g., `server.py`, `messaging.py`, `models.py`)
- Test files: `test_<module>.py` pattern (e.g., `test_models.py`, `test_tasks.py`)
- No class files since using flat module structure

**Functions:**
- snake_case for all functions (e.g., `create_team`, `send_plain_message`, `_would_create_cycle`)
- Private functions prefixed with `_` (e.g., `_teams_dir`, `_tasks_dir`, `_discriminate_member`)
- Test functions: `test_<description>` (e.g., `test_create_task_assigns_id_1_first`)

**Variables:**
- snake_case for local variables (e.g., `team_name`, `request_id`, `task_id`)
- UPPER_CASE for module-level constants (e.g., `TEAMS_DIR`, `TASKS_DIR`, `COLOR_PALETTE`)
- Private module variables prefixed with `_` (e.g., `_STATUS_ORDER`, `_VALID_NAME_RE`)

**Types:**
- PascalCase for Pydantic models (e.g., `TeamConfig`, `TaskFile`, `InboxMessage`)
- PascalCase for type aliases (e.g., `MemberUnion`)

## Code Style

**Formatting:**
- No explicit formatter config detected (no `.prettierrc`, `.black`, etc.)
- Consistent 4-space indentation observed throughout
- Line length appears around 100-120 characters based on code samples

**Linting:**
- No linter config files detected (no `.pylintrc`, `.flake8`, `ruff.toml`)
- Code uses `from __future__ import annotations` for forward reference support
- Type hints used extensively throughout (`str | None`, `Path | None`, etc.)

## Import Organization

**Order:**
1. Future imports: `from __future__ import annotations`
2. Standard library (grouped): `import asyncio`, `import json`, `from pathlib import Path`
3. Third-party packages: `from pydantic import BaseModel`, `from fastmcp import Context`
4. Local imports: `from claude_teams.models import ...`, `from claude_teams.teams import ...`

**Pattern observed:**
```python
from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel

from claude_teams.models import TeamConfig
from claude_teams.tasks import create_task
```

**Path Aliases:**
- No path aliases used
- All imports use full module paths (e.g., `from claude_teams.models import ...`)

## Error Handling

**Patterns:**
- Validation errors raise `ValueError` with descriptive messages (e.g., `src/claude_teams/tasks.py:84`)
- File operations raise `FileNotFoundError` when entities don't exist
- MCP tools wrap lower-level exceptions in `ToolError` from `fastmcp.exceptions` (e.g., `src/claude_teams/server.py:67`)
- Context managers used for resource cleanup (e.g., file locks in `src/claude_teams/messaging.py:27-34`)

**Error message format:**
```python
raise ValueError(f"Task {task_id!r} cannot block itself")
raise ValueError(f"Team {team_name!r} does not exist")
raise ToolError(f"Recipient {recipient!r} is not a member of team {team_name!r}")
```

## Logging

**Framework:** Standard `console` (no structured logging framework)

**Patterns:**
- No explicit logging observed in codebase
- Errors communicated via exceptions
- MCP tools return structured success/error responses via result models

## Comments

**When to Comment:**
- Brief inline comments for non-obvious logic (e.g., `src/claude_teams/teams.py:102` - "atomic write")
- Docstrings on MCP tool functions explaining parameters and behavior
- Phase markers in complex functions (e.g., `src/claude_teams/tasks.py:135-288` with Phase 1-4 comments)

**Style:**
```python
# NOTE(author): explanation for non-obvious implementation choice
# --- Phase 1: Read ---
# BFS from to_id through blocked_by chains
```

**JSDoc/TSDoc:**
- Not applicable (Python codebase)
- MCP tool decorators use docstrings for tool descriptions:
```python
@mcp.tool
def team_create(team_name: str, ctx: Context) -> dict:
    """Create a new agent team. Sets up team config..."""
```

## Function Design

**Size:** Functions range from 5-150 lines; complex functions like `update_task` broken into logical phases

**Parameters:**
- Keyword-only args for optional params using `*` separator (e.g., `src/claude_teams/tasks.py:117`)
- `base_dir: Path | None = None` pattern for test injection throughout
- Type hints on all parameters

**Return Values:**
- Pydantic models for structured returns (e.g., `TeamConfig`, `TaskFile`)
- MCP tools return `dict` (serialized Pydantic models via `.model_dump()`)
- Lists return typed: `list[TaskFile]`, `list[InboxMessage]`
- None for side-effect functions (e.g., `append_message`, `write_config`)

## Module Design

**Exports:**
- No explicit `__all__` declarations
- Public API defined by non-underscore-prefixed functions
- Models module exports all Pydantic models

**Barrel Files:**
- `src/claude_teams/__init__.py` is minimal (not used as barrel)
- Direct imports from specific modules (e.g., `from claude_teams.tasks import create_task`)

## Concurrency Safety

**File locking pattern:**
```python
@contextmanager
def file_lock(lock_path: Path):
    lock_path.touch(exist_ok=True)
    with open(lock_path) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Atomic writes:**
- `tempfile.mkstemp` + `os.replace` for config writes (`src/claude_teams/teams.py:103-114`)
- Ensures no partial reads during concurrent access

## Pydantic Model Conventions

**Field aliases:**
- Use `Field(alias="camelCase")` for JSON serialization (`agentId`, `createdAt`, etc.)
- Enable with `model_config = {"populate_by_name": True}` on all models

**Serialization:**
```python
data = model.model_dump(by_alias=True, exclude_none=True)
json.dumps(data)
```

**Deserialization:**
```python
obj = Model.model_validate(raw_dict)
```

---

*Convention analysis: 2026-02-07*
