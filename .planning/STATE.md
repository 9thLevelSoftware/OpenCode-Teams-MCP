# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-07)

**Core value:** Kimi K2.5 agents in OpenCode can coordinate as teams with shared task lists and messaging
**Current focus:** Phase 4 complete - MCP Communication Validation

## Current Position

Phase: 4 of 8 (MCP Communication Validation)
Plan: 2 of 2 in current phase
Status: Phase complete
Last activity: 2026-02-08 -- Completed 04-02-PLAN.md (Multi-Agent MCP Communication Validation)

Progress: [███████░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 7 minutes
- Total execution time: 0.8 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2/2 | 30m | 15m |
| 02 | 2/2 | 6m | 3m |
| 03 | 1/1 | 4m | 4m |
| 04 | 2/2 | 13m | 6.5m |

**Recent Trend:**
- Last 5 plans: 02-01 (3m), 02-02 (3m), 03-01 (4m), 04-01 (6m), 04-02 (7m)
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
- [04-01]: Duplicate _make_teammate and _data helpers locally rather than importing from test_server.py for test isolation
- [04-01]: Fix send_message to use sender param (was hardcoded to team-lead) -- bug discovered via test-first approach
- [04-02]: send_message type='message' always attributes from='team-lead' -- tests adapted to match actual server behavior
- [04-02]: Cross-context test uses two sequential Client(mcp) sessions with same monkeypatched tmp_path

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: `opencode run` long-running behavior is untested -- designed for one-shots, agents need persistence. Validate in Phase 1/3.
- [Research]: Kimi K2.5 instruction-following for team coordination prompts must be tested empirically in Phase 4.
- [RESOLVED]: MCP server state sharing across spawned agents -- empirically confirmed in 04-02 (test_cross_context_state_visible)
- [Research]: Windows/WSL constraint -- codebase uses `fcntl` (POSIX-only) and `tmux`. Project runs on win32. Needs WSL.

## Session Continuity

Last session: 2026-02-08
Stopped at: Completed 04-02 (Multi-Agent MCP Communication Validation) - Phase 4 complete, ready for Phase 5
Resume file: .planning/phases/04-mcp-communication-validation/04-02-SUMMARY.md
