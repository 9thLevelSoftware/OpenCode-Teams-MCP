---
phase: 05-agent-health-monitoring
plan: 02
subsystem: mcp-api
tags: [fastmcp, health-check, mcp-tools, pydantic, state-persistence]

# Dependency graph
requires:
  - phase: 05-agent-health-monitoring
    plan: 01
    provides: check_single_agent_health, load_health_state, save_health_state, AgentHealthStatus model
  - phase: 01-opencode-swap
    provides: TeammateMember model with tmux_pane_id field
provides:
  - check_agent_health MCP tool for single-agent health queries
  - check_all_agents_health MCP tool for batch health queries
  - Automatic health state persistence for hung detection across tool calls
affects: [phase-06, phase-07, phase-08]

# Tech tracking
tech-stack:
  added: [msvcrt (Windows compat in tasks.py)]
  patterns: [MCP tool wrapping of spawner health functions, health state load/save/update cycle per tool call]

key-files:
  created: []
  modified:
    - src/claude_teams/server.py
    - src/claude_teams/tasks.py
    - tests/test_server.py

key-decisions:
  - "Health state persistence handled in MCP tool layer (not in check_single_agent_health) for control over when state is saved"
  - "Both tools use model_dump(by_alias=True, exclude_none=True) consistent with all other server.py tools"

patterns-established:
  - "Health check MCP tools mock check_single_agent_health at server module level for testing without tmux"
  - "State persistence tested via two sequential tool calls verifying previous_hash is passed on second call"

# Metrics
duration: 5min
completed: 2026-02-08
---

# Phase 5 Plan 2: Health Check MCP Tools Summary

**Two MCP tools (check_agent_health, check_all_agents_health) exposing health detection to team lead with automatic health state persistence for hung detection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-08T16:19:37Z
- **Completed:** 2026-02-08T16:24:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- check_agent_health MCP tool returns alive/dead/hung/unknown status for a specific agent with ToolError for unknown agents
- check_all_agents_health MCP tool returns health status for all teammates (excludes lead), with batch state persistence
- Both tools automatically persist health state (content hashes + timestamps) enabling hung detection across polling calls
- 10 new integration tests covering alive/dead/hung detection, unknown agent errors, state persistence, camelCase aliases, lead exclusion, empty team handling
- Cross-platform fcntl fix applied to tasks.py (same pattern as messaging.py from 05-01)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add check_agent_health and check_all_agents_health MCP tools** - `513365e` (feat)
2. **Task 2: Add integration tests for health check MCP tools** - `f5f4b7f` (test)

## Files Created/Modified
- `src/claude_teams/server.py` - Added check_agent_health and check_all_agents_health MCP tools with health state persistence
- `src/claude_teams/tasks.py` - Fixed cross-platform fcntl import (msvcrt on Windows, fcntl on POSIX)
- `tests/test_server.py` - Added TestCheckAgentHealth (6 tests) and TestCheckAllAgentsHealth (4 tests)

## Decisions Made
- Health state persistence handled in MCP tool layer rather than in check_single_agent_health, giving the tool control over when state is saved
- Both tools use model_dump(by_alias=True, exclude_none=True) consistent with all other server.py tools

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed fcntl import failure in tasks.py on Windows**
- **Found during:** Task 1 (import verification)
- **Issue:** tasks.py imports fcntl at module level, which is POSIX-only. On Windows (win32), ModuleNotFoundError prevents any code from loading.
- **Fix:** Applied same cross-platform pattern from messaging.py (05-01): uses msvcrt.locking on Windows, fcntl.flock on POSIX.
- **Files modified:** src/claude_teams/tasks.py
- **Verification:** All imports succeed on Windows; all tests pass
- **Committed in:** 513365e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix to unblock all code execution on Windows. Same fix pattern already established in 05-01. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 5 complete: health detection functions (05-01) and MCP tools (05-02) both done
- Team lead can now call check_agent_health / check_all_agents_health to detect dead/hung agents
- Combined with existing force_kill_teammate, enables the detect-and-kill workflow (RELY-03 + RELY-04)
- Ready for Phase 6 (Supervision Loop) which can use these tools for automated monitoring

---
*Phase: 05-agent-health-monitoring*
*Completed: 2026-02-08*
