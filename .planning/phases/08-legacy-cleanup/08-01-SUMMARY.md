---
phase: 08-legacy-cleanup
plan: 01
subsystem: spawner
tags: [cleanup, legacy-removal, dead-code]

# Dependency graph
requires:
  - phase: 03-opencode-spawn-wiring
    provides: build_opencode_run_command as replacement for build_spawn_command
  - phase: 07-desktop-spawning
    provides: desktop backend path that does not use lead_session_id
provides:
  - Spawner module free of Claude Code-specific functions
  - spawn_teammate API without dead lead_session_id parameter
  - Test suite without Claude-specific test classes
affects: [08-legacy-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deletion-only refactor: remove dead code without replacing it"

key-files:
  created: []
  modified:
    - src/claude_teams/spawner.py
    - src/claude_teams/server.py
    - tests/test_spawner.py

key-decisions:
  - "SESSION_ID constant retained in tests -- still needed by create_team() fixture"
  - "lead_session_id on TeamConfig model (models.py) is NOT part of this cleanup -- it is team config state, not a dead spawn parameter"

patterns-established:
  - "spawn_teammate takes only keyword args after opencode_binary (using *,)"

# Metrics
duration: 6min
completed: 2026-02-08
---

# Phase 8 Plan 1: Legacy Claude Code Cleanup Summary

**Removed discover_claude_binary(), build_spawn_command(), and dead lead_session_id parameter from spawner module**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-08T18:15:02Z
- **Completed:** 2026-02-08T18:20:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Deleted discover_claude_binary() function and its test class (TestDiscoverClaudeBinary)
- Deleted build_spawn_command() function and its test class (TestBuildSpawnCommand) -- eliminated all Claude CLI flag generation
- Removed dead lead_session_id parameter from spawn_teammate() and all 18 test call sites plus server.py caller
- Full test suite passes (329/329 + 1 pre-existing Windows fcntl skip)

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete discover_claude_binary, build_spawn_command, and their tests** - `137062e` (refactor)
2. **Task 2: Remove lead_session_id parameter from spawn_teammate and all callers** - `95ce573` (refactor)

## Files Created/Modified
- `src/claude_teams/spawner.py` - Removed discover_claude_binary(), build_spawn_command(), and lead_session_id param from spawn_teammate()
- `src/claude_teams/server.py` - Removed lead_session_id=ls["session_id"] from spawn_teammate_tool call
- `tests/test_spawner.py` - Removed TestDiscoverClaudeBinary, TestBuildSpawnCommand classes; removed SESSION_ID from all spawn_teammate() calls; removed 2 imports

## Decisions Made
- SESSION_ID constant kept in test file -- it is still used by the team_dir fixture for create_team()
- lead_session_id field on TeamConfig model (models.py/teams.py) is a separate concept (team-level session tracking, not spawn parameter) and was NOT removed in this plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Spawner module is now free of all Claude Code-specific functions
- Ready for 08-02 which handles remaining Claude model string replacements
- No blockers

## Self-Check: PASSED

- All 3 modified files exist on disk
- Commit 137062e (Task 1) verified in git log
- Commit 95ce573 (Task 2) verified in git log
- grep for discover_claude_binary, build_spawn_command, lead_session_id in src/tests returns zero results

---
*Phase: 08-legacy-cleanup*
*Completed: 2026-02-08*
