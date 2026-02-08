# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-07)

**Core value:** Kimi K2.5 agents in OpenCode can coordinate as teams with shared task lists and messaging
**Current focus:** Phase 3 - Spawn Execution (complete)

## Current Position

Phase: 3 of 8 (Spawn Execution)
Plan: 1 of 1 in current phase
Status: Phase complete
Last activity: 2026-02-08 -- Completed 03-01-PLAN.md (OpenCode Run Command Construction)

Progress: [█████░░░░░] 30%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 8 minutes
- Total execution time: 0.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2/2 | 30m | 15m |
| 02 | 2/2 | 6m | 3m |
| 03 | 1/1 | 4m | 4m |

**Recent Trend:**
- Last 5 plans: 01-01 (15m), 01-02 (15m), 02-01 (3m), 02-02 (3m), 03-01 (4m)
- Trend: Sustained fast execution for targeted plans

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Replace Claude Code entirely, not hybrid -- clean swap of spawner module only
- [Roadmap]: Dynamic agent config generation via `.opencode/agents/<name>.md` for identity injection
- [Roadmap]: RELY-02 (permissions) mapped to Phase 2 (config gen) since it is a config concern, not a runtime reliability concern
- [01-01]: Use tuple comparison instead of packaging.version to avoid dependency risk
- [01-01]: All Claude aliases (sonnet/opus/haiku) map to kimi-k2.5 since it's the only supported model
- [01-01]: Credential references use {env:VAR_NAME} syntax per OpenCode pattern to prevent secret leakage
- [01-02]: Default provider hardcoded to 'moonshot-ai' in lifespan for Phase 1 (configurable later)
- [01-02]: Model parameter changed from Literal to str to accept both aliases and provider/model strings
- [02-01]: Permission field uses string "allow" not boolean True for OpenCode non-interactive mode
- [02-01]: claude-teams_* wildcard in frontmatter enables all MCP tools without explicit listing
- [02-01]: System prompt uses fully-qualified tool names (claude-teams_read_inbox) per MCP requirements
- [02-01]: ensure_opencode_json uses setdefault pattern to preserve existing config during merges
- [02-02]: cleanup_agent_config in spawner.py, not config_gen.py, as cleanup is lifecycle concern not config generation
- [02-02]: Use Path.cwd() as default project_dir in server.py since MCP server runs from project root
- [03-01]: Keep build_spawn_command for Phase 8 cleanup rather than deleting now
- [03-01]: Timeout wrapping via shell 'timeout' command inside tmux pane, not Python subprocess timeout

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: `opencode run` long-running behavior is untested -- designed for one-shots, agents need persistence. Validate in Phase 1/3.
- [Research]: Kimi K2.5 instruction-following for team coordination prompts must be tested empirically in Phase 4.
- [Research]: MCP server state sharing across spawned agents needs empirical confirmation in Phase 4.
- [Research]: Windows/WSL constraint -- codebase uses `fcntl` (POSIX-only) and `tmux`. Project runs on win32. Needs WSL.

## Session Continuity

Last session: 2026-02-08
Stopped at: Completed 03-01 (OpenCode Run Command Construction) - Phase 3 complete, ready for Phase 4
Resume file: .planning/phases/03-spawn-execution/03-01-SUMMARY.md
