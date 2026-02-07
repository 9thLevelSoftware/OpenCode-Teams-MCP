# Codebase Concerns

**Analysis Date:** 2026-02-07

## Tech Debt

**Windows Compatibility - fcntl file locking:**
- Issue: `fcntl` module used for file locking in `messaging.py` and `tasks.py` is Unix-only and not available on Windows
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\messaging.py` (lines 3, 27-34), `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (lines 2, 17-24)
- Impact: Code cannot run on Windows without additional dependencies or fallback to platform-specific locking mechanisms
- Fix approach: Add platform-specific file locking (use `msvcrt` for Windows, `fcntl` for Unix) or use a cross-platform library like `filelock`

**Tmux dependency limits portability:**
- Issue: Hard dependency on tmux for teammate spawning via subprocess calls
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\spawner.py` (lines 104, 123), `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\README.md` (line 55)
- Impact: Cannot use on systems without tmux (Windows without WSL, some minimal containers)
- Fix approach: Support alternative backend types beyond tmux (already has `backend_type` field in models), or document tmux as Unix-only requirement

**Config overwrites on duplicate team creation:**
- Issue: `create_team()` doesn't check if team already exists before writing config
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\teams.py` (lines 39-89)
- Impact: Silently overwrites existing team config if called twice with same name, potentially losing member data
- Fix approach: Add existence check and raise error, or document as idempotent operation with expected overwrite behavior

**No validation that Claude binary is actually Claude Code:**
- Issue: `discover_claude_binary()` checks PATH but doesn't verify binary is correct version or supports required flags
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\spawner.py` (lines 14-21)
- Impact: Could find wrong `claude` binary, spawn will fail with cryptic errors
- Fix approach: Run `claude --version` or similar check to verify compatibility

**Race condition potential in task update cycle detection:**
- Issue: Cycle detection reads task files outside the lock, concurrent updates could create cycles
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (lines 39-61, 134-297)
- Impact: Under high concurrency, circular dependencies could be introduced despite validation
- Fix approach: Consider read-write lock pattern or hold lock during cycle check phase

## Known Bugs

**Inbox mark_as_read without lock can corrupt data:**
- Symptoms: When `mark_as_read=False` path is taken, no file lock is acquired but concurrent appends can happen
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\messaging.py` (lines 84-90)
- Trigger: Concurrent reads without locking while another process appends messages
- Workaround: Always use `mark_as_read=True` for production code

**Team deletion doesn't verify empty inboxes:**
- Symptoms: Team deletion checks for non-lead members but doesn't ensure inboxes are empty or read
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\teams.py` (lines 117-134)
- Trigger: Delete team while unread messages exist
- Workaround: None - data is lost

**Empty name validation uses truthiness not explicit check:**
- Symptoms: Team/agent names with only whitespace pass regex but fail intent
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (line 83), `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\teams.py` (line 46)
- Trigger: Create team with name like "   " (passes regex `^[A-Za-z0-9_-]+$` but strips to empty)
- Workaround: Tests show this is caught for tasks (line 198-200 in test_tasks.py) but not for teams

## Security Considerations

**Command injection via team/agent names:**
- Risk: Agent names and team names are passed to shell via `shlex.quote()` in tmux spawn command
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\spawner.py` (lines 30-50)
- Current mitigation: Regex validation `^[A-Za-z0-9_-]+$` prevents shell metacharacters, `shlex.quote()` adds defense in depth
- Recommendations: Current approach is sound, ensure regex is never relaxed without security review

**Filesystem paths derived from user input:**
- Risk: Team names become directory names under `~/.claude/teams/<team-name>/`
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\teams.py` (lines 54-58), `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\messaging.py` (line 43)
- Current mitigation: Regex validation prevents directory traversal (`..`, `/`, `\` not allowed)
- Recommendations: Maintain strict name validation, document that team names are filesystem paths

**No authentication between teammates:**
- Risk: Any process that can write to `~/.claude/teams/<team>/inboxes/*.json` can inject messages
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\messaging.py` (lines 93-106)
- Current mitigation: File permissions rely on OS user model
- Recommendations: Document trust model - teammates must share same OS user or trust boundary

**Subprocess spawning inherits environment:**
- Risk: Claude binary spawned with full parent environment including potential secrets
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\spawner.py` (lines 103-108)
- Current mitigation: None - environment is inherited by default in subprocess.run
- Recommendations: Consider explicit env dict with only required vars, or document that teammates inherit parent secrets

## Performance Bottlenecks

**Sequential file I/O in list_tasks:**
- Problem: Reads all task files serially with no caching
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (lines 301-315)
- Cause: Glob all .json files then parse each with `json.loads(f.read_text())`
- Improvement path: Add pagination, caching, or index file with task metadata

**Completing task updates all dependent tasks:**
- Problem: When status changes to "completed", code iterates through all task files to clean up `blocked_by` references
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (lines 249-263)
- Cause: No index of reverse dependencies, must scan filesystem
- Improvement path: Maintain in-memory index or separate dependency graph file

**Poll inbox busy-waits with 0.5s sleep:**
- Problem: `poll_inbox` uses polling loop with fixed 500ms sleep
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\server.py` (lines 358-375)
- Cause: No filesystem watch mechanism, falls back to polling
- Improvement path: Use watchdog library or inotify for event-driven inbox monitoring

**Atomic writes create temp files in team directory:**
- Problem: Every config write creates temp file, writes data, then renames
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\teams.py` (lines 98-114)
- Cause: Ensuring atomic writes to prevent partial reads
- Improvement path: This is intentional for safety, but temp files could accumulate if crashes occur (they should be cleaned on process exit)

## Fragile Areas

**Task update transaction handling:**
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (lines 116-298)
- Why fragile: Four-phase update (read, validate, mutate, write) with complex dependency sync logic across multiple files
- Safe modification: Always add tests for new validation rules, ensure validation happens in Phase 2 before any writes in Phase 4
- Test coverage: Excellent - tests cover cycle detection, bidirectional sync, rollback on validation failure (lines 344-375)

**File locking across messaging and tasks:**
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\messaging.py` (lines 26-34), `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (lines 16-24)
- Why fragile: Duplicate lock implementations, Unix-only, relies on fcntl behavior
- Safe modification: Test on actual filesystem, not mocks, ensure locks are always released in finally blocks
- Test coverage: One threading test exists (`test_should_not_lose_message_appended_during_mark_as_read` in test_messaging.py), but no stress tests for concurrent task updates

**Pydantic model discriminators:**
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\models.py` (lines 48-62)
- Why fragile: Union type discrimination based on presence of "prompt" field
- Safe modification: Don't add "prompt" field to LeadMember or remove from TeammateMember without updating discriminator
- Test coverage: Basic serialization tested, but discriminator edge cases not explicitly tested

## Scaling Limits

**Single directory per team for all tasks:**
- Current capacity: Tested up to 15 tasks in test suite, but filesystem can handle thousands of files
- Limit: Performance degrades with >1000 tasks due to glob + parse all files in `list_tasks`
- Scaling path: Shard task files into subdirectories, add index file, or move to SQLite

**Inbox files grow unbounded:**
- Current capacity: Each inbox is append-only JSON array in single file
- Limit: With hundreds of messages, file size and parse time grow linearly
- Scaling path: Rotate inboxes (archive old messages), or implement message expiry

**No limit on team members:**
- Current capacity: COLOR_PALETTE has 8 colors, wraps with modulo
- Limit: No hard limit, but UI/UX degrades with many concurrent agents
- Scaling path: Add member count limit or document recommended maximum

**Tmux pane limit:**
- Current capacity: Tmux has soft limit around 100-200 panes per session depending on system
- Limit: Spawning hundreds of teammates will exhaust tmux capacity
- Scaling path: Support multiple tmux sessions, or alternative spawning backend

## Dependencies at Risk

**fastmcp beta version:**
- Risk: Pinned to `fastmcp==3.0.0b1` (beta release)
- Impact: API may change in stable release, could break on update
- Migration plan: Monitor fastmcp releases, pin to stable version when available

**Python 3.12+ requirement:**
- Risk: Requires bleeding-edge Python (3.12+ released Oct 2023)
- Impact: Excludes systems on LTS Python versions (3.8, 3.10)
- Migration plan: Review if 3.12-specific features are actually used, consider lowering to 3.10+

**No pinned development dependencies:**
- Risk: pytest and pytest-asyncio use `>=` constraints in pyproject.toml
- Impact: Future pytest releases could break tests
- Migration plan: Pin exact versions or use lock file

## Missing Critical Features

**No graceful shutdown timeout:**
- Problem: Shutdown request is sent but no timeout enforcement for teammate response
- Blocks: Force-kill is only option if teammate hangs on shutdown
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\server.py` (lines 168-216, 338-354)

**No inbox message expiry:**
- Problem: Inboxes accumulate all messages forever, no cleanup mechanism
- Blocks: Long-running teams will have large inbox files impacting performance

**No task priority or ordering beyond ID:**
- Problem: Tasks only have numeric ID for ordering, no priority field
- Blocks: Cannot express "urgent" vs "low priority" tasks
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\models.py` (lines 76-88)

**No agent heartbeat or liveness check:**
- Problem: No way to detect if spawned teammate crashed or is still alive
- Blocks: Dead agents stay in member list until manually removed

## Test Coverage Gaps

**No Windows-specific test runs:**
- What's not tested: fcntl fallback behavior, path separators on Windows
- Files: All modules using `fcntl`
- Risk: Complete failure on Windows deployment
- Priority: High - affects platform compatibility claim

**No concurrent task update stress tests:**
- What's not tested: Multiple agents updating tasks simultaneously
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\tasks.py` (entire file)
- Risk: Race conditions in cycle detection or bidirectional sync under load
- Priority: Medium - affects multi-agent reliability

**No integration test for full spawning workflow:**
- What's not tested: Actual tmux spawning, Claude binary interaction
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\spawner.py`
- Risk: Regressions in command building or environment passing
- Priority: Medium - current tests mock spawning

**No test for inbox message loss scenarios:**
- What's not tested: Power loss during write, disk full, permission errors
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\messaging.py`
- Risk: Message corruption or loss in adverse conditions
- Priority: Low - edge case, but impacts reliability

**No test for config atomic write failure handling:**
- What's not tested: Temp file creation failure, rename failure on cross-filesystem moves
- Files: `C:\Users\dasbl\PycharmProjects\claude-code-teams-mcp\src\claude_teams\teams.py` (lines 98-114)
- Risk: Orphaned temp files, config corruption
- Priority: Low - handled by try/finally but not verified

---

*Concerns audit: 2026-02-07*
