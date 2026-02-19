from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import yaml


OPENCODE_JSON_SCHEMA = "https://opencode-files.s3.amazonaws.com/schemas/opencode.json"


def generate_agent_config(
    agent_id: str,
    name: str,
    team_name: str,
    color: str,
    model: str,
    role_instructions: str = "",
    custom_instructions: str = "",
) -> str:
    """Generate OpenCode agent config markdown with YAML frontmatter and system prompt.

    Args:
        agent_id: Full agent identifier (e.g., "alice@team1")
        name: Agent name
        team_name: Team name
        color: Agent color from COLOR_PALETTE
        model: Model string (e.g., "openai/gpt-5.2", "moonshotai/kimi-k2.5")
        role_instructions: Optional role-specific instructions from a template.
            Injected between Identity and Communication Protocol sections.
        custom_instructions: Optional user-provided instructions per spawn.
            Wrapped with "# Additional Instructions" heading.

    Returns:
        Complete markdown config string with frontmatter and body
    """
    # Build frontmatter dict
    frontmatter = {
        "description": f"Team agent {name} on team {team_name}",
        "model": model,
        "mode": "primary",
        "permission": "allow",  # Must be string "allow", not boolean
        "tools": {
            # All builtin tools enabled
            "read": True,
            "write": True,
            "edit": True,
            "bash": True,
            "glob": True,
            "grep": True,
            "list": True,
            "webfetch": True,
            "websearch": True,
            "todoread": True,
            "todowrite": True,
            # opencode-teams MCP tools (wildcard enables all)
            "opencode-teams_*": True,
        },
    }

    # Convert frontmatter to YAML
    frontmatter_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    # Build system prompt body from sections
    body_parts: list[str] = []

    # Section 1: Agent Identity
    body_parts.append(
        textwrap.dedent(f"""\
        # Agent Identity

        You are **{name}**, a member of team **{team_name}**.

        - Agent ID: `{agent_id}`
        - Color: {color}""")
    )

    # Section 2: Available MCP Tools
    body_parts.append(
        textwrap.dedent(f"""\
        # Available MCP Tools

        You MUST use these `opencode-teams_*` MCP tools for all team coordination.
        Do NOT invent custom workflows, scripts, or coordination frameworks.

        **Team Coordination:**
        - `opencode-teams_read_config` — read team configuration
        - `opencode-teams_server_status` — check MCP server status

        **Messaging:**
        - `opencode-teams_read_inbox` — check your inbox for messages
        - `opencode-teams_send_message` — send a message to a teammate or team-lead
        - `opencode-teams_poll_inbox` — long-poll for new messages

        **Task Management:**
        - `opencode-teams_task_list` — list all tasks for the team
        - `opencode-teams_task_get` — get details of a specific task
        - `opencode-teams_task_create` — create a new task
        - `opencode-teams_task_update` — update task status or claim a task

        **Lifecycle:**
        - `opencode-teams_check_agent_health` — check health of a single agent
        - `opencode-teams_check_all_agents_health` — check health of all agents
        - `opencode-teams_process_shutdown_approved` — acknowledge shutdown""")
    )

    # Section 3: Role instructions (from template, if provided)
    if role_instructions:
        body_parts.append(role_instructions.strip())

    # Section 4: Custom instructions (user per-spawn customization, if provided)
    if custom_instructions:
        body_parts.append(f"# Additional Instructions\n\n{custom_instructions.strip()}")

    # Section 5: Workflow
    body_parts.append(
        textwrap.dedent(f"""\
        # Workflow

        Follow this loop while working:

        1. **Check inbox** — call `opencode-teams_read_inbox(team_name="{team_name}", agent_name="{name}")` every 3-5 tool calls. Always check before starting new work.
        2. **Check tasks** — call `opencode-teams_task_list(team_name="{team_name}")` to find available tasks. Claim one with `opencode-teams_task_update(team_name="{team_name}", task_id="<id>", status="in_progress", owner="{name}")`.
        3. **Do the work** — use your tools to complete the task.
        4. **Report progress** — send updates to team-lead via `opencode-teams_send_message(team_name="{team_name}", type="message", recipient="team-lead", content="<update>", summary="<short>", sender="{name}")`.
        5. **Mark done** — call `opencode-teams_task_update(team_name="{team_name}", task_id="<id>", status="completed", owner="{name}")` when finished.""")
    )

    # Section 6: Important Rules
    body_parts.append(
        textwrap.dedent("""\
        # Important Rules

        - Use `opencode-teams_*` MCP tools for ALL team communication and task management
        - Do NOT create your own coordination systems, parallel agent frameworks, or orchestration patterns
        - Do NOT use slash commands or skills from other projects for team coordination
        - Focus on your assigned task — report to team-lead when done or blocked
        - When uncertain, ask team-lead via `opencode-teams_send_message` rather than improvising""")
    )

    # Section 7: Shutdown Protocol
    body_parts.append(
        textwrap.dedent("""\
        # Shutdown Protocol

        When you receive a `shutdown_request` message, acknowledge it and prepare to exit gracefully.""")
    )

    body = "\n\n".join(body_parts)

    # Combine frontmatter and body
    config = f"---\n{frontmatter_yaml}---\n\n{body}\n"

    return config


def cleanup_agent_config(project_dir: Path, name: str) -> None:
    """Clean up agent config file when agent is killed or removed.

    Args:
        project_dir: Project root directory containing .opencode/agents/
        name: Agent name (used to derive config filename)
    """
    config_file = project_dir / ".opencode" / "agents" / f"{name}.md"
    config_file.unlink(missing_ok=True)


def write_agent_config(
    project_dir: Path,
    name: str,
    config_content: str,
) -> Path:
    """Write agent config to .opencode/agents/<name>.md

    Creates the .opencode/agents directory if it doesn't exist.
    Overwrites existing file (re-spawn scenario).

    Args:
        project_dir: Project root directory
        name: Agent name (used for filename)
        config_content: Complete markdown config content

    Returns:
        Path to the created config file
    """
    agents_dir = project_dir / ".opencode" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    config_path = agents_dir / f"{name}.md"
    config_path.write_text(config_content, encoding="utf-8")

    return config_path


def ensure_opencode_json(
    project_dir: Path,
    mcp_server_command: str,
    mcp_server_env: dict[str, str] | None = None,
) -> Path:
    """Create or update opencode.json in the project root with opencode-teams MCP server entry.

    OpenCode reads its configuration from ``opencode.json`` (or ``opencode.jsonc``)
    in the project root — NOT from ``.opencode/config.json``.
    See: https://opencode.ai/docs/config/

    If opencode.json exists, preserves all existing keys and merges the opencode-teams
    MCP entry. If it doesn't exist, creates a new file with schema and MCP config.

    Args:
        project_dir: Project root directory
        mcp_server_command: Command to start MCP server (e.g., "uv run opencode-teams")
        mcp_server_env: Optional environment variables for MCP server

    Returns:
        Path to opencode.json
    """
    opencode_json_path = project_dir / "opencode.json"

    # Read existing or create new
    if opencode_json_path.exists():
        content = json.loads(opencode_json_path.read_text(encoding="utf-8"))
    else:
        content = {
            "$schema": OPENCODE_JSON_SCHEMA,
        }

    # Ensure mcp section exists
    content.setdefault("mcp", {})

    # OpenCode expects MCP entries as McpLocalConfig objects with type + command array
    # See: @opencode-ai/sdk types.gen.d.ts McpLocalConfig
    command_parts = mcp_server_command.split()

    mcp_entry: dict[str, Any] = {
        "type": "local",
        "command": command_parts,
        "enabled": True,
    }
    if mcp_server_env:
        mcp_entry["environment"] = mcp_server_env

    content["mcp"]["opencode-teams"] = mcp_entry

    # Write back
    opencode_json_path.write_text(
        json.dumps(content, indent=2) + "\n",
        encoding="utf-8",
    )

    return opencode_json_path
