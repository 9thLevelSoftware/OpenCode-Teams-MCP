---
phase: 06-agent-templates
plan: 02
subsystem: api
tags: [mcp, templates, spawner, agent-roles, system-prompt]

# Dependency graph
requires:
  - phase: 06-agent-templates/06-01
    provides: "AgentTemplate dataclass, TEMPLATES registry, get_template(), list_templates(), generate_agent_config with role_instructions/custom_instructions params"
provides:
  - "spawn_teammate with role_instructions and custom_instructions forwarding"
  - "spawn_teammate_tool with template param resolving to role_instructions"
  - "spawn_teammate_tool with custom_instructions param for per-spawn customization"
  - "list_agent_templates MCP tool for template discovery"
  - "subagent_type derived from template name"
affects: [phase-07, phase-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Template lookup in MCP tool layer, role_instructions passthrough to spawner/config_gen"
    - "Derived subagent_type from template name (template or 'general-purpose')"

key-files:
  created: []
  modified:
    - "src/claude_teams/spawner.py"
    - "src/claude_teams/server.py"
    - "tests/test_spawner.py"
    - "tests/test_server.py"

key-decisions:
  - "Template lookup happens in server.py (MCP tool layer), not spawner.py -- spawner receives resolved role_instructions string"
  - "subagent_type is derived from template name in server.py, not passed as separate param by caller"
  - "Replaced subagent_type param with template param on spawn_teammate_tool (breaking API change for callers that used subagent_type directly)"

patterns-established:
  - "Template resolution at MCP tool boundary: server.py does get_template(), passes role_instructions down"
  - "Custom instructions as pass-through: no validation, just forwarded to config_gen"

# Metrics
duration: 3min
completed: 2026-02-08
---

# Phase 6 Plan 2: Template Spawn Wiring Summary

**Template-aware spawn flow with template param on MCP tool, custom_instructions per-spawn customization, and list_agent_templates discovery tool**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-08T17:00:18Z
- **Completed:** 2026-02-08T17:03:46Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Wired role_instructions and custom_instructions through spawn_teammate to generate_agent_config
- Added template param to spawn_teammate_tool with get_template() lookup and ToolError for unknown templates
- Added list_agent_templates MCP tool returning all 4 templates with name and description
- 12 new tests (4 spawner + 8 server) all passing; all existing tests unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire template params through spawner.py** - `ec43577` (feat)
2. **Task 2: Add template/custom_instructions to spawn_teammate_tool + list_agent_templates** - `ee1a86f` (feat)

## Files Created/Modified
- `src/claude_teams/spawner.py` - Added role_instructions and custom_instructions keyword params to spawn_teammate(), forwarded to generate_agent_config()
- `src/claude_teams/server.py` - Replaced subagent_type with template param, added template lookup, added custom_instructions param, added list_agent_templates MCP tool
- `tests/test_spawner.py` - Added TestSpawnWithTemplate class (4 tests: role, custom, clean, both)
- `tests/test_server.py` - Added TestListAgentTemplates (2 tests) and TestSpawnWithTemplateTool (6 tests)

## Decisions Made
- Template lookup happens in server.py (MCP tool layer), not spawner.py -- keeps spawner generic, server handles template resolution
- subagent_type is derived from template name (`template or "general-purpose"`) rather than being a separate caller-provided param
- Replaced subagent_type param with template param on spawn_teammate_tool -- cleaner API since subagent_type was always meant to describe the role

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 complete: template registry (06-01) and spawn wiring (06-02) both done
- All 4 templates (researcher, implementer, reviewer, tester) discoverable via list_agent_templates
- Spawning with template produces role-specific system prompts in agent config files
- Custom instructions enable per-spawn customization beyond templates
- Ready for Phase 7

---
*Phase: 06-agent-templates*
*Completed: 2026-02-08*
