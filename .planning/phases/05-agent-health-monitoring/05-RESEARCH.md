# Phase 5: Agent Health & Monitoring - Research

**Researched:** 2026-02-07
**Domain:** tmux pane liveness detection, hung agent detection via output monitoring, force-kill and cleanup
**Confidence:** HIGH

## Summary

Phase 5 adds health monitoring to the existing agent spawning infrastructure. The system must answer three questions about each spawned agent: (1) is its tmux pane still alive? (2) if alive, is the agent actually producing output or is it hung? (3) if unresponsive, how do we kill it and clean up?

tmux provides native format variables (`pane_dead`, `pane_dead_status`, `pane_pid`) and the `remain-on-exit` window option that together give us everything needed for liveness detection. For hung agent detection, tmux's `capture-pane` command lets us snapshot pane content at intervals and compare -- if content hasn't changed over a configurable duration, the agent is hung. The existing `force_kill_teammate` MCP tool in `server.py` already implements the kill+cleanup flow (kill pane, remove member, reset tasks, cleanup config), so Phase 5 is primarily about **detection**, not action.

The key design decision is whether to use `remain-on-exit` on agent panes. Without it, a dead agent's pane disappears entirely and `tmux display-message -t %<id>` fails with a non-zero exit code -- which IS the liveness signal. With it, the pane stays around as "dead" and we can query `pane_dead` / `pane_dead_status`. The simpler approach (no `remain-on-exit`) is recommended because the existing spawn flow already works without it, and a missing pane is an unambiguous "dead" signal.

**Primary recommendation:** Add a `check_agent_health()` function to `spawner.py` that queries tmux pane status via `tmux display-message -p -t <pane_id> '#{pane_dead}'` with subprocess error handling. Add a `detect_hung_agent()` function that uses `tmux capture-pane -p -t <pane_id>` to snapshot content and compares against a previous snapshot. Expose both via new MCP tools `check_agent_health` and `check_all_agents_health`. The existing `force_kill_teammate` handles the kill+cleanup action.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `subprocess` | 3.12+ | Execute tmux commands for pane queries | Already used throughout spawner.py for tmux interaction |
| Python stdlib `hashlib` | 3.12+ | Hash pane content snapshots for efficient comparison | Avoids storing full pane text; SHA-256 of content is sufficient |
| Python stdlib `time` | 3.12+ | Timestamps for "last seen active" tracking | Already used in spawner.py and messaging.py |
| Python stdlib `dataclasses` or Pydantic | 3.12+ | Health status result models | Pydantic already used throughout codebase for all models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Existing `spawner.kill_tmux_pane()` | Codebase | Kill a tmux pane by ID | Called by existing `force_kill_teammate` after health check determines agent is dead/hung |
| Existing `teams.read_config()` | Codebase | Read team config to enumerate agent pane IDs | Used to iterate all agents for batch health check |
| Existing `server.force_kill_teammate()` | Codebase | Full kill+cleanup flow | Already exists, already exposed as MCP tool. Phase 5 detection feeds into this existing action. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw `subprocess.run` tmux calls | `libtmux` Python library | libtmux adds a dependency (currently 0 non-essential deps); raw subprocess is consistent with existing codebase pattern |
| `capture-pane` content hashing | `tmux monitor-silence` option | `monitor-silence` triggers visual alerts in tmux UI, not programmatic callbacks; we need programmatic detection, not visual feedback |
| `capture-pane` content hashing | `pipe-pane` to log file + check mtime | `pipe-pane` requires per-pane setup at spawn time and produces persistent log files; `capture-pane` is a point-in-time query, simpler and no side effects |
| Per-pane `remain-on-exit` | No `remain-on-exit` (current) | `remain-on-exit` keeps dead panes visible; without it, pane disappears = dead. Simpler to detect, no window option management needed. Recommended: no `remain-on-exit`. |
| Polling-based health checks | tmux hooks (`pane-died`, `pane-exited`) | Hooks require tmux configuration side effects; polling from Python is simpler and testable. Hooks don't work programmatically -- they run tmux commands, not Python callbacks. |

**Installation:**
```bash
# No new dependencies -- all stdlib + existing codebase modules
```

## Architecture Patterns

### Recommended Project Structure
```
src/claude_teams/
  spawner.py          # ADD: check_pane_alive(), capture_pane_content(), health check functions
  server.py           # ADD: check_agent_health, check_all_agents_health MCP tools
  models.py           # ADD: AgentHealthStatus model
  teams.py            # UNCHANGED
  messaging.py        # UNCHANGED
  tasks.py            # UNCHANGED
  config_gen.py       # UNCHANGED
```

### Pattern 1: Pane Liveness Check via tmux display-message
**What:** Query whether a tmux pane exists and whether its process has exited.
**When to use:** When checking if an agent's OpenCode process is still running.
**Example:**
```python
# Source: tmux man page (man7.org/linux/man-pages/man1/tmux.1.html)
# tmux display-message returns non-zero if pane doesn't exist
import subprocess

def check_pane_alive(pane_id: str) -> bool:
    """Check if a tmux pane exists and is alive.

    Returns True if the pane exists and its process is still running.
    Returns False if the pane doesn't exist (process exited, pane closed)
    or if the pane is in 'dead' state (remain-on-exit mode).

    Without remain-on-exit: pane disappears when process exits,
    so subprocess.run returns non-zero -> False.

    With remain-on-exit: pane persists but pane_dead=1 -> False.
    """
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_dead}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            # Pane doesn't exist (already closed)
            return False
        # pane_dead is "1" if dead, "0" if alive
        return result.stdout.strip() == "0"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### Pattern 2: Hung Agent Detection via Content Snapshots
**What:** Capture pane content at intervals and compare to detect lack of output change.
**When to use:** When an agent's pane is alive but may be hung (no progress).
**Example:**
```python
# Source: tmux capture-pane docs
import hashlib
import subprocess

def capture_pane_content_hash(pane_id: str) -> str | None:
    """Capture current pane content and return its hash.

    Returns None if pane doesn't exist or capture fails.
    Returns SHA-256 hex digest of pane content otherwise.
    """
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", pane_id],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return hashlib.sha256(result.stdout.encode()).hexdigest()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
```

### Pattern 3: Health Status Model
**What:** Structured result for agent health checks.
**When to use:** Return value from health check MCP tools.
**Example:**
```python
from pydantic import BaseModel, Field
from typing import Literal

class AgentHealthStatus(BaseModel):
    model_config = {"populate_by_name": True}

    agent_name: str = Field(alias="agentName")
    pane_id: str = Field(alias="paneId")
    status: Literal["alive", "dead", "hung", "unknown"]
    # For alive agents: hash of last captured pane content
    last_content_hash: str | None = Field(alias="lastContentHash", default=None)
    # For dead agents: exit code if available
    exit_status: int | None = Field(alias="exitStatus", default=None)
    # Human-readable detail
    detail: str = ""
```

### Pattern 4: Batch Health Check with Team Config
**What:** Check all agents in a team and return combined health status.
**When to use:** For the `check_all_agents_health` MCP tool.
**Example:**
```python
def check_all_agents_health(team_name: str) -> list[AgentHealthStatus]:
    """Check health of all teammates in the team.

    Reads team config, iterates all TeammateMember entries,
    checks pane liveness for each.
    """
    config = teams.read_config(team_name)
    results = []
    for member in config.members:
        if isinstance(member, TeammateMember):
            status = check_agent_health(member.name, member.tmux_pane_id)
            results.append(status)
    return results
```

### Anti-Patterns to Avoid

- **Using `tmux list-panes` and parsing multi-line output:** `list-panes` lists ALL panes in a window/session; it requires parsing. Use `display-message -t <pane_id>` to query a specific pane directly.
- **Storing full pane content for comparison:** Pane content can be large (thousands of lines of scrollback). Hash the content instead -- a SHA-256 digest is sufficient to detect changes.
- **Using `tmux monitor-silence` for programmatic detection:** `monitor-silence` triggers tmux visual alerts (status bar highlighting), not programmatic callbacks. It doesn't provide an API we can query from Python.
- **Relying on `is_active` field in TeammateMember:** The `is_active` field is currently never set to `True` anywhere in the codebase. It's metadata, not a health indicator. Health must be checked via tmux.
- **Running health checks in the MCP tool handler itself as a blocking loop:** Health checks should be point-in-time queries, not background polling loops. The MCP client (team lead) calls `check_agent_health` when it wants to know, not continuously.
- **Killing an agent without cleanup:** Always use the existing `force_kill_teammate` flow which does: kill pane + remove member + reset tasks + cleanup config. Never just call `kill_tmux_pane` alone.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pane existence check | Custom PID tracking / `ps aux` parsing | `tmux display-message -p -t <pane_id> '#{pane_dead}'` | tmux knows its own pane state; PID tracking is fragile across shell layers |
| Pane content capture | Custom log file tailing / `pipe-pane` | `tmux capture-pane -p -t <pane_id>` | Point-in-time query, no setup, no cleanup, no persistent files |
| Content change detection | Full-text diff comparison | `hashlib.sha256(content)` comparison | Hash comparison is O(1) storage, O(n) compute; diff is unnecessary complexity |
| Kill + cleanup flow | New kill function | Existing `force_kill_teammate` MCP tool | Already implemented, tested, handles pane kill + member removal + task reset + config cleanup |
| Agent enumeration | Querying tmux directly for pane list | `teams.read_config()` to get member pane IDs | Team config is the source of truth for which panes belong to which agents |

**Key insight:** Phase 5 is about DETECTION, not ACTION. The action (force-kill + cleanup) already exists as `force_kill_teammate` in server.py. We need to add the ability to detect when that action should be triggered.

## Common Pitfalls

### Pitfall 1: Pane ID Becomes Invalid After Kill
**What goes wrong:** After calling `kill_tmux_pane`, the pane ID (e.g., `%42`) is gone from tmux. Subsequent `display-message -t %42` calls fail. If the system doesn't update team config, it will keep trying to check a nonexistent pane.
**Why it happens:** Pane IDs are assigned by tmux and are only valid while the pane exists.
**How to avoid:** After detecting a dead pane and processing it (via `force_kill_teammate`), the member is removed from team config. Health checks should only query pane IDs from current team config members.
**Warning signs:** Repeated "pane not found" errors in health check results.

### Pitfall 2: capture-pane Returns Empty for New Panes
**What goes wrong:** Immediately after spawning, `capture-pane -p` may return empty or near-empty content. A naive "content hasn't changed" check would falsely flag a brand new agent as hung.
**Why it happens:** The agent is still starting up -- loading MCP server, connecting to API, etc.
**How to avoid:** Include a "grace period" concept: don't flag an agent as hung until it has been alive for at least N seconds (e.g., 30-60 seconds after spawn). Track `joined_at` from TeammateMember for this.
**Warning signs:** Newly spawned agents immediately flagged as hung.

### Pitfall 3: tmux capture-pane Hangs on Some Panes
**What goes wrong:** There are known tmux issues where `capture-pane -p -S-` (capturing full scrollback) can hang on certain panes.
**Why it happens:** tmux bug with scrollback capture on specific pane states (documented in tmux issue #251 for libtmux).
**How to avoid:** Use `capture-pane -p` without `-S-` (captures only visible content, not full scrollback). Use `subprocess.run(timeout=5)` to prevent indefinite hangs.
**Warning signs:** Health check subprocess times out on specific panes.

### Pitfall 4: Content Hash Changes Without Meaningful Progress
**What goes wrong:** An agent's pane content changes (cursor blink, timestamp updates, spinner) but the agent isn't actually making progress on its task.
**Why it happens:** Some terminal output is cosmetic, not substantive.
**How to avoid:** Since we use `--format json` for OpenCode agents, output should be structured JSON, not spinner/animation output. Content hash changes should correlate with actual work. If this becomes a problem, can refine by parsing the JSON output for meaningful progress indicators. For Phase 5, hash-based detection is sufficient.
**Warning signs:** Agent marked as "alive" despite making no task progress. This is a future concern beyond Phase 5.

### Pitfall 5: Race Condition Between Health Check and Kill
**What goes wrong:** Two concurrent operations: (1) health check reads pane_id from config, (2) force_kill_teammate removes member from config. Now health check tries to query a removed agent.
**Why it happens:** Team config reads and writes are not globally locked.
**How to avoid:** Health check functions should handle `KeyError` / missing member gracefully. If a member is not found in config during a batch health check, skip it (it was already removed). The existing `teams.write_config` uses atomic writes (tempfile + os.replace), minimizing but not eliminating the window.
**Warning signs:** Intermittent "member not found" errors during health checks.

### Pitfall 6: tmux Not Running
**What goes wrong:** The tmux server itself may have crashed or been killed. All pane queries fail with "no server running" or "failed to connect to server".
**Why it happens:** tmux server crash, user manually kills tmux, system resource exhaustion.
**How to avoid:** Catch `subprocess.CalledProcessError` and `FileNotFoundError` from tmux commands. If tmux itself is unreachable, report all agents as "unknown" status rather than crashing.
**Warning signs:** All health checks return "unknown" simultaneously.

## Code Examples

Verified patterns from tmux documentation and existing codebase:

### Complete check_pane_alive Implementation
```python
# Source: tmux man page - display-message, pane_dead format variable
import subprocess

def check_pane_alive(pane_id: str) -> bool:
    """Check if a tmux pane exists and its process is still running.

    Uses tmux display-message to query the pane_dead format variable.
    If the pane doesn't exist (non-zero return code), returns False.
    If the pane exists but process has exited (pane_dead=1), returns False.
    If the pane exists and process is running (pane_dead=0), returns True.

    Args:
        pane_id: tmux pane identifier (e.g., "%42")

    Returns:
        True if pane is alive, False otherwise.
    """
    if not pane_id:
        return False
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_dead}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        return result.stdout.strip() == "0"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### Complete capture_pane_content_hash Implementation
```python
# Source: tmux man page - capture-pane command
import hashlib
import subprocess

def capture_pane_content_hash(pane_id: str) -> str | None:
    """Capture visible pane content and return its SHA-256 hash.

    Uses tmux capture-pane -p to get current visible content.
    Does NOT use -S- to avoid known hangs with full scrollback capture.

    Args:
        pane_id: tmux pane identifier (e.g., "%42")

    Returns:
        SHA-256 hex digest of pane content, or None if capture fails.
    """
    if not pane_id:
        return None
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", pane_id],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return hashlib.sha256(result.stdout.encode()).hexdigest()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
```

### Health Check Function Combining Liveness + Hung Detection
```python
# Source: Combining tmux queries with existing team config
import time
from claude_teams.models import AgentHealthStatus, TeammateMember

# Default: consider agent hung if no output change for 120 seconds
DEFAULT_HUNG_TIMEOUT_SECONDS = 120
# Grace period after spawn before hung detection kicks in
DEFAULT_GRACE_PERIOD_SECONDS = 60

def check_single_agent_health(
    member: TeammateMember,
    previous_hash: str | None = None,
    last_change_time: float | None = None,
    hung_timeout: int = DEFAULT_HUNG_TIMEOUT_SECONDS,
    grace_period: int = DEFAULT_GRACE_PERIOD_SECONDS,
) -> AgentHealthStatus:
    """Check health of a single agent.

    1. Check if pane is alive
    2. If alive, capture content hash and compare to previous
    3. If content unchanged for > hung_timeout seconds, mark as hung

    Args:
        member: TeammateMember from team config
        previous_hash: Hash from last health check (None if first check)
        last_change_time: Epoch time when content last changed (None if first check)
        hung_timeout: Seconds of no output change before marking hung
        grace_period: Seconds after spawn before hung detection applies

    Returns:
        AgentHealthStatus with current status
    """
    pane_id = member.tmux_pane_id

    # Step 1: Is pane alive?
    if not check_pane_alive(pane_id):
        return AgentHealthStatus(
            agent_name=member.name,
            pane_id=pane_id,
            status="dead",
            detail="Pane no longer exists or process has exited",
        )

    # Step 2: Capture content hash
    current_hash = capture_pane_content_hash(pane_id)
    if current_hash is None:
        return AgentHealthStatus(
            agent_name=member.name,
            pane_id=pane_id,
            status="unknown",
            detail="Could not capture pane content",
        )

    # Step 3: Check for hung (no output change)
    now = time.time()
    agent_age_seconds = (now * 1000 - member.joined_at) / 1000

    if agent_age_seconds < grace_period:
        # Still in grace period -- don't flag as hung
        return AgentHealthStatus(
            agent_name=member.name,
            pane_id=pane_id,
            status="alive",
            last_content_hash=current_hash,
            detail=f"Alive (grace period, {int(agent_age_seconds)}s since spawn)",
        )

    if previous_hash is not None and current_hash == previous_hash:
        # Content hasn't changed since last check
        if last_change_time is not None:
            stale_seconds = now - last_change_time
            if stale_seconds >= hung_timeout:
                return AgentHealthStatus(
                    agent_name=member.name,
                    pane_id=pane_id,
                    status="hung",
                    last_content_hash=current_hash,
                    detail=f"No output change for {int(stale_seconds)}s (threshold: {hung_timeout}s)",
                )

    return AgentHealthStatus(
        agent_name=member.name,
        pane_id=pane_id,
        status="alive",
        last_content_hash=current_hash,
        detail="Alive and producing output",
    )
```

### MCP Tool for Health Check
```python
# Source: Following existing server.py MCP tool pattern
@mcp.tool
def check_agent_health(
    team_name: str,
    agent_name: str,
) -> dict:
    """Check the health status of a specific agent.
    Returns status: 'alive', 'dead', 'hung', or 'unknown'.
    Dead agents have exited or their pane no longer exists.
    Hung agents are alive but producing no new output."""
    config = teams.read_config(team_name)
    for m in config.members:
        if isinstance(m, TeammateMember) and m.name == agent_name:
            alive = check_pane_alive(m.tmux_pane_id)
            status = AgentHealthStatus(
                agent_name=m.name,
                pane_id=m.tmux_pane_id,
                status="alive" if alive else "dead",
                detail="Pane alive" if alive else "Pane dead or missing",
            )
            return status.model_dump(by_alias=True, exclude_none=True)
    raise ToolError(f"Agent {agent_name!r} not found in team {team_name!r}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No health detection | tmux `display-message` + `pane_dead` format variable | Phase 5 (now) | System can detect dead agents programmatically |
| No hung detection | `capture-pane` content hashing at intervals | Phase 5 (now) | System can detect unresponsive agents |
| Manual force-kill only | `force_kill_teammate` already exists; Phase 5 adds automatic detection | Phase 5 (now) | Detection + existing action = complete health management |
| `is_active` field unused | Still unused; health determined by tmux state | Phase 5 (now) | Could update `is_active` based on health checks (optional) |

**Deprecated/outdated:**
- `is_active` field on TeammateMember: Never set to True anywhere. Health checks via tmux are the actual source of truth. Could be updated by health checks but is not required for detection.

## Requirements Mapping

| Requirement | How Satisfied | Verification |
|-------------|---------------|--------------|
| **RELY-03**: System can detect dead/hung agents via tmux pane status | `check_pane_alive()` queries `pane_dead` format variable; `capture_pane_content_hash()` compares snapshots over time for hung detection | Unit test: mock subprocess returns for alive/dead/hung scenarios |
| **RELY-04**: System can force-kill unresponsive OpenCode instances | Existing `force_kill_teammate` already kills pane + removes member + resets tasks + cleans config. Phase 5 adds detection that feeds into this existing action. | Unit test: verify `force_kill_teammate` correctly invokes `kill_tmux_pane` and cleanup steps (already tested in existing test suite) |

## Open Questions

1. **Hung timeout duration**
   - What we know: `opencode run` loops up to 1000 tool-call steps. Between steps, there should be output (JSON format). API rate limiting can cause pauses.
   - What's unclear: How long a normal "thinking pause" is between tool calls. 120 seconds is a guess.
   - Recommendation: Default to 120 seconds, make it configurable. This is generous enough to avoid false positives from API latency but tight enough to catch truly hung processes. Can be tuned empirically.

2. **Stateful vs. stateless hung detection**
   - What we know: Hung detection requires comparing content over time. A single point-in-time check can only tell alive/dead, not hung.
   - What's unclear: Where to store the previous content hash and last-change timestamp between MCP tool calls.
   - Recommendation: Two options: (a) Store in a file alongside team config (e.g., `~/.claude/teams/<name>/health.json`), or (b) Pass previous hash/timestamp as parameters to the MCP tool (caller tracks state). Option (a) is better for the batch `check_all_agents_health` tool; option (b) is simpler but pushes tracking to the client. **Recommend option (a)** -- a health state file persisted alongside team config, updated on each health check call.

3. **Should health checks auto-kill dead agents?**
   - What we know: `force_kill_teammate` removes the member from config and resets tasks. The team lead may want to inspect a dead agent's state before cleanup.
   - What's unclear: Whether auto-kill is desirable or if detection-only is better.
   - Recommendation: Detection-only by default. Return the health status and let the MCP client (team lead) decide whether to call `force_kill_teammate`. A separate `auto_cleanup_dead_agents` tool or parameter could be added if desired, but Phase 5 focuses on detection.

4. **Should the check_agent_health tool also attempt to get exit status?**
   - What we know: `tmux display-message -p -t <pane_id> '#{pane_dead_status}'` can return the exit code of a dead pane, but only if `remain-on-exit` is on (otherwise pane is gone).
   - What's unclear: Whether exit status is valuable enough to justify enabling `remain-on-exit`.
   - Recommendation: Skip exit status for Phase 5. The primary value is alive/dead/hung classification. Exit status would require `remain-on-exit` which adds complexity. Can be added later if needed.

## Sources

### Primary (HIGH confidence)
- [tmux man page (man7.org)](https://man7.org/linux/man-pages/man1/tmux.1.html) -- `pane_dead`, `pane_dead_status`, `pane_pid` format variables; `display-message`, `capture-pane`, `remain-on-exit`, `monitor-silence` documentation
- [tmux Formats wiki (GitHub)](https://github.com/tmux/tmux/wiki/Formats) -- Format variable system, conditional format expressions
- [tmux Advanced Use wiki (GitHub)](https://github.com/tmux/tmux/wiki/Advanced-Use) -- Monitor-silence, monitor-activity, hooks
- Existing codebase `spawner.py` -- `kill_tmux_pane()`, `spawn_teammate()` tmux subprocess patterns
- Existing codebase `server.py` -- `force_kill_teammate()` full kill+cleanup flow, `process_shutdown_approved()` graceful removal

### Secondary (MEDIUM confidence)
- [tmux respawn-pane guide (tmuxai.dev)](https://tmuxai.dev/tmux-respawn-pane/) -- `remain-on-exit` behavior, `pane-died` hook, practical detection patterns
- [tmux capture-pane guide (tmuxai.dev)](https://tmuxai.dev/tmux-capture-pane/) -- `capture-pane -p` usage, `-S` flag behavior
- [tmux alerts and monitoring (tmuxai.dev)](https://tmuxai.dev/tmux-alerts-monitoring/) -- `monitor-silence` option, activity detection
- [Baeldung tmux logging guide](https://www.baeldung.com/linux/tmux-logging) -- `capture-pane` and `pipe-pane` patterns for content extraction
- [libtmux capture-pane hang issue #251](https://github.com/tmux-python/libtmux/issues/251) -- Known issue with `capture-pane -S-` hanging

### Tertiary (LOW confidence)
- Optimal hung timeout (120s) -- engineering judgment, no empirical data for OpenCode agent workloads
- Content hash approach for hung detection -- sound in theory, untested with actual OpenCode JSON output patterns

## Metadata

**Confidence breakdown:**
- Pane liveness detection: HIGH -- `tmux display-message` with `pane_dead` is well-documented and unambiguous
- Content capture for hung detection: HIGH -- `tmux capture-pane -p` is well-documented; SHA-256 hashing is standard
- Hung detection logic: MEDIUM -- the approach is sound but timeout thresholds and grace periods need empirical tuning
- Integration with existing kill flow: HIGH -- `force_kill_teammate` already exists and is tested
- Health state persistence: MEDIUM -- file-based storage alongside team config is consistent with codebase patterns but specifics not validated

**Research date:** 2026-02-07
**Valid until:** 2026-02-21 (14 days -- tmux API is very stable, approach is straightforward)
