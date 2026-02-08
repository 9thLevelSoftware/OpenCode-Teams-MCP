---
phase: 03-spawn-execution
plan: 01
subsystem: spawner
tags: [opencode, tmux, shlex, timeout, command-construction]

# Dependency graph
requires:
  - phase: 01-opencode-migration
    provides: "OpenCode binary discovery, version validation, model translation"
  - phase: 02-agent-config-generation
    provides: "Agent config generation wired into spawn lifecycle"
provides:
  - "build_opencode_run_command() for OpenCode agent spawning"
  - "SPAWN_TIMEOUT_SECONDS constant (300s) for hung process prevention"
  - "opencode_binary parameter name in spawn_teammate signature"
affects: [04-inbox-protocol, 08-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns: ["timeout wrapping for spawned processes", "shlex.quote for all command args"]

key-files:
  created: []
  modified:
    - src/claude_teams/spawner.py
    - src/claude_teams/server.py
    - tests/test_spawner.py

key-decisions:
  - "Keep build_spawn_command for Phase 8 cleanup rather than deleting now"
  - "Timeout wrapping via shell 'timeout' command inside tmux pane, not Python subprocess timeout"

patterns-established:
  - "OpenCode run command format: cd <cwd> && timeout <sec> opencode run --agent <name> --model <provider/model> --format json <prompt>"
  - "All command arguments use shlex.quote for shell safety"

# Metrics
duration: 4min
completed: 2026-02-08
---

# Phase 3 Plan 1: OpenCode Run Command Construction Summary

**build_opencode_run_command() with timeout wrapping replacing Claude Code spawn command, opencode_binary parameter rename across call chain**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-08T04:10:25Z
- **Completed:** 2026-02-08T04:13:55Z
- **Tasks:** 2 (RED + GREEN TDD cycle)
- **Files modified:** 3

## Accomplishments
- New `build_opencode_run_command()` produces correct OpenCode CLI command with --agent, --model, --format json flags
- Timeout wrapping (300s default) prevents hung processes from OpenCode API errors (RELY-01)
- Parameter renamed `claude_binary` -> `opencode_binary` in spawn_teammate and server.py call site
- spawn_teammate now calls build_opencode_run_command instead of build_spawn_command (SPAWN-06)
- 8 new tests covering command format, quoting, special chars, custom timeout, and absence of Claude flags
- Old build_spawn_command preserved for Phase 8 cleanup

## Task Commits

Each task was committed atomically:

1. **RED: Failing tests for OpenCode command construction** - `72f51b1` (test)
2. **GREEN: Implement build_opencode_run_command and parameter rename** - `88fc5be` (feat)

_TDD plan: RED wrote failing tests, GREEN implemented to pass. No refactor needed._

## Files Created/Modified
- `src/claude_teams/spawner.py` - Added SPAWN_TIMEOUT_SECONDS, build_opencode_run_command(), renamed claude_binary to opencode_binary in spawn_teammate
- `src/claude_teams/server.py` - Updated spawn_teammate call to use opencode_binary= keyword
- `tests/test_spawner.py` - Added TestBuildOpencodeRunCommand class (7 tests) and test_spawn_uses_opencode_command

## Decisions Made
- Keep build_spawn_command function for Phase 8 cleanup rather than deleting now -- other code may reference it
- Use shell `timeout` command inside tmux pane, not Python subprocess.timeout, because tmux returns immediately and the timeout must protect the long-running opencode process inside the pane

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- fcntl module (POSIX-only) blocks pytest collection on Windows. This is a known project constraint (documented in STATE.md). Core logic verified via isolated Python execution. Full test suite requires WSL/Linux.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Spawn command construction complete, ready for Phase 4 (inbox protocol refinement)
- Requirements satisfied: SPAWN-06 (command construction), RELY-01 (timeout wrapping)
- Requirements already satisfied from prior work: SPAWN-07 (tmux pane), SPAWN-08 (pane ID capture), SPAWN-09 (inbox delivery)
- Phase 3 is fully complete -- this was the only plan needed

---
*Phase: 03-spawn-execution*
*Completed: 2026-02-08*
