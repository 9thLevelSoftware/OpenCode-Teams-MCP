# Testing Patterns

**Analysis Date:** 2026-02-07

## Test Framework

**Runner:**
- pytest 8.0+
- Config: `pyproject.toml` lines 27-29

**Assertion Library:**
- pytest native assertions (no separate library)

**Run Commands:**
```bash
pytest                 # Run all tests
pytest tests/          # Run tests directory
pytest -v              # Verbose mode
```

## Test File Organization

**Location:**
- Co-located in `tests/` directory (not alongside source)
- One test file per source module

**Naming:**
- Pattern: `test_<module>.py`
- Examples: `test_models.py`, `test_tasks.py`, `test_messaging.py`, `test_teams.py`

**Structure:**
```
tests/
├── __init__.py
├── conftest.py               # Shared fixtures
├── test_models.py            # Tests for src/claude_teams/models.py
├── test_tasks.py             # Tests for src/claude_teams/tasks.py
├── test_messaging.py         # Tests for src/claude_teams/messaging.py
├── test_teams.py             # Tests for src/claude_teams/teams.py
├── test_server.py            # Tests for src/claude_teams/server.py
└── test_spawner.py           # Tests for src/claude_teams/spawner.py
```

## Test Structure

**Suite Organization:**
```python
class TestFeatureName:
    def test_specific_behavior(self, fixture1, fixture2):
        # Arrange
        obj = create_thing()

        # Act
        result = obj.do_something()

        # Assert
        assert result == expected
```

**Patterns:**
- Test classes group related tests by feature area (e.g., `TestColorPalette`, `TestLeadMember`)
- Class names: `TestCamelCase`
- Test function names: `test_snake_case_description`
- Descriptive test names explain the behavior being verified (e.g., `test_create_task_assigns_id_1_first`)
- Some tests use standalone functions (not in classes) when testing single operations

**Example from `tests/test_models.py:25-34`:**
```python
class TestColorPalette:
    def test_has_8_colors(self):
        assert len(COLOR_PALETTE) == 8

    def test_blue_first(self):
        assert COLOR_PALETTE[0] == "blue"
```

## Fixtures

**Framework:** pytest fixtures

**Patterns:**
```python
@pytest.fixture
def tmp_claude_dir(tmp_path: Path) -> Path:
    teams_dir = tmp_path / "teams"
    teams_dir.mkdir()
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    return tmp_path
```

**Location:**
- Shared fixtures in `tests/conftest.py`
- Module-specific fixtures defined at top of test files

**Common fixtures:**
- `tmp_claude_dir` (from `conftest.py`) - Sets up temp team/task directories
- `team_tasks_dir` (in `test_tasks.py`) - Pre-creates a test team
- `team_dir` (in `test_messaging.py`) - Creates team directory structure

**Usage pattern:**
- Fixtures passed as function parameters
- `base_dir=tmp_claude_dir` pattern used throughout for filesystem isolation

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**
```python
with unittest.mock.patch("os.replace", side_effect=OSError("disk full")):
    with pytest.raises(OSError, match="disk full"):
        write_config("atomic", config, base_dir=tmp_claude_dir)
```

**Example from `tests/test_teams.py:153`:**
- Mock used to simulate failure conditions (e.g., disk full during atomic write)
- Verify cleanup behavior when operations fail

**What to Mock:**
- External system calls (e.g., `os.replace` for testing error handling)
- Not commonly used in this codebase - prefers integration-style tests with real filesystem

**What NOT to Mock:**
- File operations use real temp directories via `tmp_path` fixture
- JSON serialization/deserialization tested directly
- Pydantic model validation tested with real instances

## Test Data

**Pattern - Factory functions:**
```python
def _make_teammate(name: str, team_name: str) -> TeammateMember:
    return TeammateMember(
        agent_id=f"{name}@{team_name}",
        name=name,
        agent_type="teammate",
        model="claude-sonnet-4-20250514",
        prompt="Do stuff",
        color="blue",
        plan_mode_required=False,
        joined_at=int(time.time() * 1000),
        tmux_pane_id="%1",
        cwd="/tmp",
    )
```

**Pattern - Inline creation:**
```python
task = create_task("test-team", "First", "desc", base_dir=tmp_claude_dir)
```

**Location:**
- Helper factories defined at top of test modules (e.g., `tests/test_teams.py:21`)
- Simple test data created inline in test functions

## Coverage

**Requirements:** No explicit coverage target configured

**View Coverage:**
```bash
pytest --cov=src/claude_teams --cov-report=html
pytest --cov=src/claude_teams --cov-report=term
```

**Note:** Coverage tools not in project dependencies, would need manual install

## Test Types

**Unit Tests:**
- Pure function tests (e.g., `tests/test_models.py` - model serialization)
- Business logic tests (e.g., `tests/test_tasks.py` - task state transitions)
- Isolated with temp directories via fixtures

**Integration Tests:**
- File system operations (e.g., `tests/test_messaging.py` - inbox read/write)
- Multi-module interactions (e.g., task creation → team validation)
- Concurrency tests (e.g., `test_messaging.py:167` - file locking behavior)

**E2E Tests:**
- Not present in test suite
- MCP server integration not tested
- No tests for spawning actual Claude Code processes

## Common Patterns

**Async Testing:**
- Config: `asyncio_mode = "auto"` in `pyproject.toml:29`
- Tests can be async without explicit decorators:
```python
async def test_async_operation():
    result = await async_function()
    assert result
```

**Error Testing:**
```python
with pytest.raises(ValueError, match="subject must not be empty"):
    create_task("test-team", "", "desc", base_dir=tmp_claude_dir)

with pytest.raises(RuntimeError):
    delete_team("busy", base_dir=tmp_claude_dir)
```

**Round-trip Testing:**
```python
def test_round_trip_with_lead_only(self):
    # Create object
    config = TeamConfig(name="test", ...)

    # Serialize
    raw = json.loads(config.model_dump_json(by_alias=True))

    # Verify serialized format
    assert raw["createdAt"] == 1770398183858

    # Deserialize and verify
    restored = TeamConfig.model_validate(raw)
    assert restored.name == "test"
```

**File System Testing:**
```python
def test_create_task_excludes_none_owner(tmp_claude_dir, team_tasks_dir):
    task = create_task("test-team", "Sub", "desc", base_dir=tmp_claude_dir)
    raw = json.loads((team_tasks_dir / f"{task.id}.json").read_text())
    assert "owner" not in raw
```

**Boundary Testing:**
- Empty inputs: `test_create_task_rejects_empty_subject`
- Max lengths: `test_should_reject_name_exceeding_max_length`
- State transitions: `test_update_task_rejects_backward_status_transition`

**Concurrency Testing:**
```python
def test_should_not_lose_message_appended_during_mark_as_read(tmp_claude_dir):
    # Uses threading + fcntl to verify lock behavior
    completed = threading.Event()
    with open(lock_path) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        reader = threading.Thread(target=do_read)
        reader.start()
        completed_without_lock = completed.wait(timeout=1.0)
```

**Validation Testing:**
- Circular dependency detection: `test_rejects_simple_circular_dependency`
- Duplicate prevention: `test_should_reject_duplicate_member_name`
- State constraints: `test_update_task_rejects_start_when_blocked`

---

*Testing analysis: 2026-02-07*
