from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from opencode_teams import teams, messaging
from opencode_teams.models import AgentHealthStatus, COLOR_PALETTE, TeammateMember
from opencode_teams.spawner import (
    assign_color,
    build_opencode_run_command,
    build_windows_terminal_command,
    capture_pane_content_hash,
    check_pane_alive,
    check_process_alive,
    check_single_agent_health,
    cleanup_agent_config,
    discover_desktop_binary,
    discover_opencode_binary,
    kill_desktop_process,
    kill_tmux_pane,
    launch_desktop_app,
    load_health_state,
    save_health_state,
    spawn_teammate,
    translate_model,
    validate_opencode_version,
    DEFAULT_GRACE_PERIOD_SECONDS,
    DEFAULT_HUNG_TIMEOUT_SECONDS,
    DESKTOP_BINARY_ENV_VAR,
    DESKTOP_BINARY_NAMES,
    DESKTOP_PATHS,
    MINIMUM_OPENCODE_VERSION,
    SPAWN_TIMEOUT_SECONDS,
)
from opencode_teams.model_discovery import (
    discover_models,
    resolve_model_string,
    select_model_by_preference,
)
from opencode_teams.models import ModelInfo, ModelPreference


TEAM = "test-team"
SESSION_ID = "test-session-id"


@pytest.fixture
def team_dir(tmp_base_dir: Path) -> Path:
    teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)
    return tmp_base_dir


def _make_member(
    name: str,
    team: str = TEAM,
    color: str = "blue",
    model: str = "sonnet",
    agent_type: str = "general-purpose",
    cwd: str = "/tmp",
) -> TeammateMember:
    return TeammateMember(
        agent_id=f"{name}@{team}",
        name=name,
        agent_type=agent_type,
        model=model,
        prompt=f"You are {name}",
        color=color,
        joined_at=0,
        tmux_pane_id="",
        cwd=cwd,
    )


class TestAssignColor:
    def test_first_teammate_is_blue(self, team_dir: Path) -> None:
        color = assign_color(TEAM, base_dir=team_dir)
        assert color == "blue"

    def test_cycles(self, team_dir: Path) -> None:
        for i in range(len(COLOR_PALETTE)):
            member = _make_member(f"agent-{i}", color=COLOR_PALETTE[i])
            teams.add_member(TEAM, member, base_dir=team_dir)

        color = assign_color(TEAM, base_dir=team_dir)
        assert color == COLOR_PALETTE[0]


def _make_opencode_member(
    name: str = "researcher",
    team: str = TEAM,
    color: str = "blue",
    model: str = "moonshot-ai/kimi-k2.5",
    agent_type: str = "general-purpose",
    cwd: str = "/tmp",
    prompt: str = "Do research",
    plan_mode_required: bool = False,
) -> TeammateMember:
    return TeammateMember(
        agent_id=f"{name}@{team}",
        name=name,
        agent_type=agent_type,
        model=model,
        prompt=prompt,
        color=color,
        joined_at=0,
        tmux_pane_id="",
        cwd=cwd,
        plan_mode_required=plan_mode_required,
    )


class TestBuildOpencodeRunCommand:
    def test_basic_command_format(self) -> None:
        member = _make_opencode_member()
        cmd = build_opencode_run_command(member, "/usr/local/bin/opencode")
        assert "opencode" in cmd
        assert "run" in cmd
        assert "--agent" in cmd
        assert "researcher" in cmd
        assert "--model" in cmd
        assert "moonshot-ai/kimi-k2.5" in cmd
        assert "--format json" in cmd
        assert "timeout 300" in cmd
        assert "cd" in cmd
        assert "/tmp" in cmd

    def test_prompt_is_shell_quoted(self) -> None:
        member = _make_opencode_member(prompt="Fix 'main.py' bugs")
        cmd = build_opencode_run_command(member, "/usr/local/bin/opencode")
        # shlex.quote wraps strings with single quotes; the inner quotes
        # are escaped. The key test: no unquoted single quotes break the shell.
        assert "Fix" in cmd
        assert "main.py" in cmd
        assert "bugs" in cmd

    def test_special_chars_in_prompt(self) -> None:
        member = _make_opencode_member(prompt='Use "$HOME" and `backticks`')
        cmd = build_opencode_run_command(member, "/usr/local/bin/opencode")
        # shlex.quote should safely wrap the prompt
        assert "$HOME" in cmd
        assert "backticks" in cmd

    def test_custom_timeout(self) -> None:
        member = _make_opencode_member()
        cmd = build_opencode_run_command(member, "/usr/local/bin/opencode", timeout_seconds=600)
        assert "timeout 600" in cmd
        assert "timeout 300" not in cmd

    def test_no_claude_flags(self) -> None:
        member = _make_opencode_member()
        cmd = build_opencode_run_command(member, "/usr/local/bin/opencode")
        assert "--agent-id" not in cmd
        assert "--team-name" not in cmd
        assert "--parent-session-id" not in cmd
        assert "--agent-color" not in cmd
        assert "--agent-type" not in cmd
        assert "CLAUDECODE" not in cmd
        assert "CLAUDE_CODE_EXPERIMENTAL" not in cmd

    def test_no_plan_mode_flag(self) -> None:
        member = _make_opencode_member(plan_mode_required=True)
        cmd = build_opencode_run_command(member, "/usr/local/bin/opencode")
        assert "--plan-mode-required" not in cmd

    def test_default_timeout_constant(self) -> None:
        assert SPAWN_TIMEOUT_SECONDS == 300


class TestSpawnTeammateNameValidation:
    def test_should_reject_empty_name(self, team_dir: Path) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            spawn_teammate(TEAM, "", "prompt", "/bin/echo", base_dir=team_dir)

    def test_should_reject_name_with_special_chars(self, team_dir: Path) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            spawn_teammate(TEAM, "agent!@#", "prompt", "/bin/echo", base_dir=team_dir)

    def test_should_reject_name_exceeding_64_chars(self, team_dir: Path) -> None:
        with pytest.raises(ValueError, match="too long"):
            spawn_teammate(TEAM, "a" * 65, "prompt", "/bin/echo", base_dir=team_dir)

    def test_should_reject_reserved_name_team_lead(self, team_dir: Path) -> None:
        with pytest.raises(ValueError, match="reserved"):
            spawn_teammate(TEAM, "team-lead", "prompt", "/bin/echo", base_dir=team_dir)


class TestSpawnTeammate:
    @patch("opencode_teams.spawner.subprocess")
    def test_registers_member_before_spawn(
        self, mock_subprocess: MagicMock, team_dir: Path
    ) -> None:
        mock_subprocess.run.return_value.stdout = "%42\n"
        spawn_teammate(
            TEAM,
            "researcher",
            "Do research",
            "/usr/local/bin/claude",
            base_dir=team_dir,
        )
        config = teams.read_config(TEAM, base_dir=team_dir)
        names = [m.name for m in config.members]
        assert "researcher" in names

    @patch("opencode_teams.spawner.subprocess")
    def test_writes_prompt_to_inbox(
        self, mock_subprocess: MagicMock, team_dir: Path
    ) -> None:
        mock_subprocess.run.return_value.stdout = "%42\n"
        spawn_teammate(
            TEAM,
            "researcher",
            "Do research",
            "/usr/local/bin/claude",
            base_dir=team_dir,
        )
        msgs = messaging.read_inbox(TEAM, "researcher", base_dir=team_dir)
        assert len(msgs) == 1
        assert msgs[0].from_ == "team-lead"
        assert msgs[0].text == "Do research"

    @patch("opencode_teams.spawner.subprocess")
    def test_updates_pane_id(
        self, mock_subprocess: MagicMock, team_dir: Path
    ) -> None:
        mock_subprocess.run.return_value.stdout = "%42\n"
        member = spawn_teammate(
            TEAM,
            "researcher",
            "Do research",
            "/usr/local/bin/opencode",
            base_dir=team_dir,
        )
        assert member.tmux_pane_id == "%42"
        config = teams.read_config(TEAM, base_dir=team_dir)
        found = [m for m in config.members if m.name == "researcher"]
        assert found[0].tmux_pane_id == "%42"

    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_uses_opencode_command(
        self, mock_subprocess: MagicMock, team_dir: Path
    ) -> None:
        """Verify spawn_teammate calls tmux with opencode run command, not Claude flags."""
        mock_subprocess.run.return_value.stdout = "%42\n"
        spawn_teammate(
            TEAM,
            "researcher",
            "Do research",
            "/usr/local/bin/opencode",
            base_dir=team_dir,
        )
        # Get the tmux command string (last positional arg to subprocess.run)
        call_args = mock_subprocess.run.call_args[0][0]
        tmux_cmd = call_args[-1]  # The shell command passed to tmux split-window
        assert "opencode" in tmux_cmd
        assert "run" in tmux_cmd
        assert "CLAUDECODE" not in tmux_cmd


class TestSpawnWithTemplate:
    """Tests for template wiring in spawn flow (role_instructions, custom_instructions)."""

    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_passes_role_instructions_to_config_gen(
        self, mock_subprocess: MagicMock, tmp_base_dir: Path, tmp_path: Path
    ) -> None:
        mock_subprocess.run.return_value.stdout = "%42\n"
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spawn_teammate(
            TEAM,
            "researcher",
            "Do research",
            "/usr/local/bin/opencode",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
            model="moonshot-ai/kimi-k2.5",
            role_instructions="# Role: Tester\n\nTest stuff.",
        )

        config_file = project_dir / ".opencode" / "agents" / "researcher.md"
        assert config_file.exists()
        content = config_file.read_text()
        assert "# Role: Tester" in content

    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_passes_custom_instructions_to_config_gen(
        self, mock_subprocess: MagicMock, tmp_base_dir: Path, tmp_path: Path
    ) -> None:
        mock_subprocess.run.return_value.stdout = "%42\n"
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spawn_teammate(
            TEAM,
            "worker",
            "Do work",
            "/usr/local/bin/opencode",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
            model="moonshot-ai/kimi-k2.5",
            custom_instructions="Focus on edge cases.",
        )

        config_file = project_dir / ".opencode" / "agents" / "worker.md"
        assert config_file.exists()
        content = config_file.read_text()
        assert "Focus on edge cases." in content

    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_without_template_produces_clean_config(
        self, mock_subprocess: MagicMock, tmp_base_dir: Path, tmp_path: Path
    ) -> None:
        mock_subprocess.run.return_value.stdout = "%42\n"
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spawn_teammate(
            TEAM,
            "generic",
            "Do generic work",
            "/usr/local/bin/opencode",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
            model="moonshot-ai/kimi-k2.5",
        )

        config_file = project_dir / ".opencode" / "agents" / "generic.md"
        assert config_file.exists()
        content = config_file.read_text()
        assert "# Role:" not in content
        assert "# Additional Instructions" not in content

    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_with_both_role_and_custom_instructions(
        self, mock_subprocess: MagicMock, tmp_base_dir: Path, tmp_path: Path
    ) -> None:
        mock_subprocess.run.return_value.stdout = "%42\n"
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spawn_teammate(
            TEAM,
            "hybrid",
            "Do hybrid work",
            "/usr/local/bin/opencode",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
            model="moonshot-ai/kimi-k2.5",
            role_instructions="# Role: Tester\n\nTest everything.",
            custom_instructions="Focus on performance tests.",
        )

        config_file = project_dir / ".opencode" / "agents" / "hybrid.md"
        assert config_file.exists()
        content = config_file.read_text()
        assert "# Role: Tester" in content
        assert "Focus on performance tests." in content
        # Role instructions should appear before custom instructions
        role_pos = content.index("# Role: Tester")
        custom_pos = content.index("# Additional Instructions")
        workflow_pos = content.index("# Workflow")
        assert role_pos < custom_pos < workflow_pos


class TestKillTmuxPane:
    @patch("opencode_teams.spawner.subprocess")
    def test_calls_subprocess(self, mock_subprocess: MagicMock) -> None:
        kill_tmux_pane("%99")
        mock_subprocess.run.assert_called_once_with(
            ["tmux", "kill-pane", "-t", "%99"], check=False
        )


# OpenCode tests


class TestDiscoverOpencodeBinary:
    @patch("opencode_teams.spawner.subprocess.run")
    @patch("opencode_teams.spawner.shutil.which")
    def test_found_and_valid_version(
        self, mock_which: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_which.return_value = "/usr/local/bin/opencode"
        mock_run.return_value.stdout = "1.1.52\n"
        mock_run.return_value.stderr = ""
        assert discover_opencode_binary() == "/usr/local/bin/opencode"
        mock_which.assert_called_once_with("opencode")

    @patch("opencode_teams.spawner.shutil.which")
    def test_not_found(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError, match="opencode"):
            discover_opencode_binary()

    @patch("opencode_teams.spawner.subprocess.run")
    @patch("opencode_teams.spawner.shutil.which")
    def test_version_too_old(
        self, mock_which: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_which.return_value = "/usr/local/bin/opencode"
        mock_run.return_value.stdout = "1.1.40\n"
        mock_run.return_value.stderr = ""
        with pytest.raises(RuntimeError, match="too old"):
            discover_opencode_binary()

    @patch("opencode_teams.spawner.subprocess.run")
    @patch("opencode_teams.spawner.shutil.which")
    def test_version_with_v_prefix(
        self, mock_which: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_which.return_value = "/usr/local/bin/opencode"
        mock_run.return_value.stdout = "v1.1.53\n"
        mock_run.return_value.stderr = ""
        assert discover_opencode_binary() == "/usr/local/bin/opencode"

    @patch("opencode_teams.spawner.subprocess.run")
    @patch("opencode_teams.spawner.shutil.which")
    def test_version_with_verbose_output(
        self, mock_which: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_which.return_value = "/usr/local/bin/opencode"
        mock_run.return_value.stdout = "opencode version v1.1.52\n"
        mock_run.return_value.stderr = ""
        assert discover_opencode_binary() == "/usr/local/bin/opencode"


class TestValidateOpencodeVersion:
    @patch("opencode_teams.spawner.subprocess.run")
    def test_valid_version(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "1.1.52\n"
        mock_run.return_value.stderr = ""
        assert validate_opencode_version("/usr/local/bin/opencode") == "1.1.52"

    @patch("opencode_teams.spawner.subprocess.run")
    def test_newer_version(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "2.0.0\n"
        mock_run.return_value.stderr = ""
        assert validate_opencode_version("/usr/local/bin/opencode") == "2.0.0"

    @patch("opencode_teams.spawner.subprocess.run")
    def test_old_version_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "1.1.49\n"
        mock_run.return_value.stderr = ""
        with pytest.raises(RuntimeError, match="too old"):
            validate_opencode_version("/usr/local/bin/opencode")

    @patch("opencode_teams.spawner.subprocess.run")
    def test_unparseable_output_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "unknown\n"
        mock_run.return_value.stderr = ""
        with pytest.raises(RuntimeError, match="Could not parse"):
            validate_opencode_version("/usr/local/bin/opencode")

    @patch("opencode_teams.spawner.subprocess.run")
    def test_timeout_raises(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="opencode", timeout=10
        )
        with pytest.raises(RuntimeError, match="Timed out"):
            validate_opencode_version("/usr/local/bin/opencode")

    @patch("opencode_teams.spawner.subprocess.run")
    def test_binary_not_found_raises(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError
        with pytest.raises(RuntimeError):
            validate_opencode_version("/usr/local/bin/opencode")


class TestModelDiscovery:
    """Tests for dynamic model discovery from OpenCode config."""

    def test_discover_models_from_dict(self) -> None:
        """Test discovering models from a config dict."""
        config = {
            "provider": {
                "openai": {
                    "models": {
                        "gpt-5.2-medium": {
                            "name": "GPT 5.2 Medium",
                            "limit": {"context": 272000, "output": 128000},
                            "modalities": {"input": ["text", "image"], "output": ["text"]},
                            "options": {"reasoningEffort": "medium"},
                        }
                    }
                }
            }
        }
        models = discover_models(config)
        assert len(models) == 1
        assert models[0].provider == "openai"
        assert models[0].model_id == "gpt-5.2-medium"
        assert models[0].full_model_string == "openai/gpt-5.2-medium"
        assert models[0].context_window == 272000
        assert models[0].reasoning_effort == "medium"

    def test_discover_models_multiple_providers(self) -> None:
        """Test discovering models from multiple providers."""
        config = {
            "provider": {
                "openai": {"models": {"gpt-5": {"name": "GPT 5"}}},
                "google": {"models": {"gemini-3": {"name": "Gemini 3"}}},
            }
        }
        models = discover_models(config)
        assert len(models) == 2
        providers = {m.provider for m in models}
        assert providers == {"openai", "google"}

    def test_discover_models_empty_config(self) -> None:
        """Test with empty config returns empty list."""
        assert discover_models({}) == []
        assert discover_models({"provider": {}}) == []


class TestModelSelection:
    """Tests for preference-based model selection."""

    @pytest.fixture
    def sample_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                provider="openai",
                model_id="gpt-5.2-low",
                name="GPT 5.2 Low",
                full_model_string="openai/gpt-5.2-low",
                context_window=272000,
                max_output=128000,
                input_modalities=["text", "image"],
                output_modalities=["text"],
                reasoning_effort="low",
            ),
            ModelInfo(
                provider="openai",
                model_id="gpt-5.2-high",
                name="GPT 5.2 High",
                full_model_string="openai/gpt-5.2-high",
                context_window=272000,
                max_output=128000,
                input_modalities=["text", "image"],
                output_modalities=["text"],
                reasoning_effort="high",
            ),
            ModelInfo(
                provider="google",
                model_id="gemini-3-flash",
                name="Gemini 3 Flash",
                full_model_string="google/gemini-3-flash",
                context_window=1048576,
                max_output=65536,
                input_modalities=["text", "image", "pdf"],
                output_modalities=["text"],
                reasoning_effort=None,
            ),
        ]

    def test_select_by_reasoning_effort(self, sample_models: list[ModelInfo]) -> None:
        """Test selecting model by reasoning effort."""
        pref = ModelPreference(reasoning_effort="high")
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        assert selected.reasoning_effort == "high"

    def test_select_prefer_speed(self, sample_models: list[ModelInfo]) -> None:
        """Test prefer_speed selects lower reasoning models."""
        pref = ModelPreference(prefer_speed=True)
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        # Should prefer low reasoning over high
        assert selected.reasoning_effort in ("low", None)

    def test_select_by_provider(self, sample_models: list[ModelInfo]) -> None:
        """Test filtering by provider."""
        pref = ModelPreference(provider="google")
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        assert selected.provider == "google"

    def test_select_by_min_context(self, sample_models: list[ModelInfo]) -> None:
        """Test filtering by minimum context window."""
        pref = ModelPreference(min_context_window=500000)
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        assert selected.context_window >= 500000

    def test_select_no_match(self, sample_models: list[ModelInfo]) -> None:
        """Test returns None when no models match constraints."""
        pref = ModelPreference(provider="anthropic")
        selected = select_model_by_preference(sample_models, pref)
        assert selected is None


class TestResolveModelString:
    """Tests for model string resolution."""

    @pytest.fixture
    def sample_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                provider="openai",
                model_id="gpt-5.2-medium",
                name="GPT 5.2 Medium",
                full_model_string="openai/gpt-5.2-medium",
                context_window=272000,
                max_output=128000,
            ),
        ]

    def test_passthrough_full_string(self, sample_models: list[ModelInfo]) -> None:
        """Full provider/model strings pass through unchanged."""
        result = resolve_model_string("openai/gpt-5.2-medium", sample_models)
        assert result == "openai/gpt-5.2-medium"

    def test_resolve_by_model_id(self, sample_models: list[ModelInfo]) -> None:
        """Model IDs are resolved to full strings."""
        result = resolve_model_string("gpt-5.2-medium", sample_models)
        assert result == "openai/gpt-5.2-medium"

    def test_auto_selects_model(self, sample_models: list[ModelInfo]) -> None:
        """'auto' selects a model based on preferences."""
        result = resolve_model_string("auto", sample_models)
        assert result == "openai/gpt-5.2-medium"

    def test_unknown_model_passthrough(self, sample_models: list[ModelInfo]) -> None:
        """Unknown model IDs pass through for OpenCode to validate."""
        result = resolve_model_string("unknown-model", sample_models)
        assert result == "unknown-model"


class TestTranslateModel:
    """Tests for translate_model function which wraps model_discovery."""

    def test_passthrough_provider_model(self) -> None:
        """Full provider/model strings pass through unchanged."""
        # Create mock models list
        models = [
            ModelInfo(
                provider="openai",
                model_id="gpt-5",
                name="GPT 5",
                full_model_string="openai/gpt-5",
            )
        ]
        result = translate_model("openai/gpt-5", models=models)
        assert result == "openai/gpt-5"

    def test_passthrough_arbitrary(self) -> None:
        """Arbitrary provider/model strings pass through."""
        result = translate_model("custom/my-model", models=[])
        assert result == "custom/my-model"

    def test_auto_with_models(self) -> None:
        """Auto selection works with available models."""
        models = [
            ModelInfo(
                provider="google",
                model_id="gemini-3",
                name="Gemini 3",
                full_model_string="google/gemini-3",
            )
        ]
        result = translate_model("auto", models=models)
        assert result == "google/gemini-3"


class TestConfigGenIntegration:
    """Integration tests for config generation wiring in spawn flow."""

    @patch("opencode_teams.spawner.validate_opencode_version")
    @patch("opencode_teams.spawner.shutil.which")
    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_generates_agent_config(
        self, mock_subprocess: MagicMock, mock_which: MagicMock,
        mock_validate: MagicMock, tmp_base_dir: Path, tmp_path: Path
    ) -> None:
        """Verify spawn_teammate generates .opencode/agents/<name>.md"""
        mock_which.return_value = "/usr/local/bin/opencode"
        mock_validate.return_value = "1.1.52"
        mock_subprocess.run.return_value.stdout = "%42\n"

        # Create team using tmp_base_dir for team data
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)

        # Use tmp_path as project_dir for config files
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spawn_teammate(
            TEAM,
            "researcher",
            "Do research",
            "/usr/local/bin/opencode",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
            model="moonshot-ai/kimi-k2.5",
        )

        # Verify agent config file exists
        config_file = project_dir / ".opencode" / "agents" / "researcher.md"
        assert config_file.exists()

        # Verify content has expected YAML frontmatter
        content = config_file.read_text()
        assert "mode: primary" in content
        assert "permission: allow" in content
        assert "researcher" in content
        assert TEAM in content

    @patch("opencode_teams.spawner.validate_opencode_version")
    @patch("opencode_teams.spawner.shutil.which")
    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_creates_opencode_config_json(
        self, mock_subprocess: MagicMock, mock_which: MagicMock,
        mock_validate: MagicMock, tmp_base_dir: Path, tmp_path: Path
    ) -> None:
        """Verify spawn_teammate creates opencode.json in project root with MCP server entry"""
        mock_which.return_value = "/usr/local/bin/opencode"
        mock_validate.return_value = "1.1.52"
        mock_subprocess.run.return_value.stdout = "%43\n"

        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)

        project_dir = tmp_path / "project2"
        project_dir.mkdir()

        spawn_teammate(
            TEAM,
            "worker",
            "Do work",
            "/usr/local/bin/opencode",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
        )

        # Verify opencode.json exists in project root
        opencode_json = project_dir / "opencode.json"
        assert opencode_json.exists()

        # Verify content has opencode-teams MCP entry as McpLocalConfig
        import json
        content = json.loads(opencode_json.read_text())
        assert "mcp" in content
        assert "opencode-teams" in content["mcp"]
        # OpenCode expects MCP entries as McpLocalConfig objects
        mcp_entry = content["mcp"]["opencode-teams"]
        assert mcp_entry["type"] == "local"
        assert mcp_entry["command"] == ["uv", "run", "opencode-teams"]
        assert mcp_entry["enabled"] is True

    def test_cleanup_agent_config_removes_file(self, tmp_path: Path) -> None:
        """Verify cleanup_agent_config removes the config file"""
        from opencode_teams.spawner import cleanup_agent_config

        # Create fake agent config file
        agents_dir = tmp_path / ".opencode" / "agents"
        agents_dir.mkdir(parents=True)
        config_file = agents_dir / "test-agent.md"
        config_file.write_text("# Test config")

        assert config_file.exists()

        # Call cleanup
        cleanup_agent_config(tmp_path, "test-agent")

        # Verify file is gone
        assert not config_file.exists()

    def test_cleanup_agent_config_noop_if_missing(self, tmp_path: Path) -> None:
        """Verify cleanup_agent_config doesn't error if file doesn't exist"""
        from opencode_teams.spawner import cleanup_agent_config

        # Call cleanup on nonexistent file - should not raise
        cleanup_agent_config(tmp_path, "nonexistent")

        # No assertion needed - test passes if no exception raised


# Agent health detection tests


class TestCheckPaneAlive:
    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_true_for_alive_pane(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "0\n"
        mock_run.return_value.returncode = 0
        assert check_pane_alive("%42") is True

    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_false_for_dead_pane(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "1\n"
        mock_run.return_value.returncode = 0
        assert check_pane_alive("%42") is False

    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_false_for_missing_pane(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        assert check_pane_alive("%42") is False

    def test_returns_false_for_empty_pane_id(self) -> None:
        # No subprocess call should be made
        assert check_pane_alive("") is False

    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_false_on_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="tmux", timeout=5)
        assert check_pane_alive("%42") is False

    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_false_when_tmux_not_installed(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError
        assert check_pane_alive("%42") is False


class TestCapturePaneContentHash:
    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_hash_for_live_pane(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "some output\n"
        mock_run.return_value.returncode = 0
        result = capture_pane_content_hash("%42")
        assert result is not None
        assert len(result) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in result)

    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_none_for_failed_capture(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        assert capture_pane_content_hash("%42") is None

    def test_returns_none_for_empty_pane_id(self) -> None:
        assert capture_pane_content_hash("") is None

    @patch("opencode_teams.spawner.subprocess.run")
    def test_returns_none_on_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="tmux", timeout=5)
        assert capture_pane_content_hash("%42") is None

    @patch("opencode_teams.spawner.subprocess.run")
    def test_same_content_produces_same_hash(self, mock_run: MagicMock) -> None:
        mock_run.return_value.stdout = "deterministic content"
        mock_run.return_value.returncode = 0
        hash1 = capture_pane_content_hash("%42")
        hash2 = capture_pane_content_hash("%42")
        assert hash1 == hash2

    @patch("opencode_teams.spawner.subprocess.run")
    def test_different_content_produces_different_hash(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "content A"
        hash_a = capture_pane_content_hash("%42")
        mock_run.return_value.stdout = "content B"
        hash_b = capture_pane_content_hash("%42")
        assert hash_a != hash_b


class TestCheckSingleAgentHealth:
    @patch("opencode_teams.spawner.capture_pane_content_hash")
    @patch("opencode_teams.spawner.check_pane_alive")
    def test_dead_when_pane_missing(
        self, mock_alive: MagicMock, mock_hash: MagicMock
    ) -> None:
        mock_alive.return_value = False
        member = _make_opencode_member(name="worker", prompt="Do work")
        member.joined_at = int(time.time() * 1000) - 120_000
        member.tmux_pane_id = "%42"
        result = check_single_agent_health(member, None, None)
        assert result.status == "dead"
        assert result.agent_name == "worker"
        assert result.pane_id == "%42"

    @patch("opencode_teams.spawner.capture_pane_content_hash")
    @patch("opencode_teams.spawner.check_pane_alive")
    def test_alive_when_pane_exists_and_content_changes(
        self, mock_alive: MagicMock, mock_hash: MagicMock
    ) -> None:
        mock_alive.return_value = True
        mock_hash.return_value = "newhash"
        member = _make_opencode_member(name="worker", prompt="Do work")
        member.joined_at = int(time.time() * 1000) - 120_000
        member.tmux_pane_id = "%42"
        result = check_single_agent_health(member, "oldhash", time.time() - 10)
        assert result.status == "alive"
        assert result.last_content_hash == "newhash"

    @patch("opencode_teams.spawner.capture_pane_content_hash")
    @patch("opencode_teams.spawner.check_pane_alive")
    def test_hung_when_content_unchanged_beyond_timeout(
        self, mock_alive: MagicMock, mock_hash: MagicMock
    ) -> None:
        mock_alive.return_value = True
        mock_hash.return_value = "samehash"
        member = _make_opencode_member(name="worker", prompt="Do work")
        member.joined_at = int(time.time() * 1000) - 120_000
        member.tmux_pane_id = "%42"
        result = check_single_agent_health(
            member, "samehash", time.time() - 130
        )
        assert result.status == "hung"

    @patch("opencode_teams.spawner.capture_pane_content_hash")
    @patch("opencode_teams.spawner.check_pane_alive")
    def test_alive_during_grace_period(
        self, mock_alive: MagicMock, mock_hash: MagicMock
    ) -> None:
        mock_alive.return_value = True
        mock_hash.return_value = "samehash"
        # 5 seconds ago -- well within default 60s grace period
        member = _make_opencode_member(name="worker", prompt="Do work")
        member.joined_at = int(time.time() * 1000) - 5_000
        member.tmux_pane_id = "%42"
        result = check_single_agent_health(
            member, "samehash", time.time() - 130
        )
        assert result.status == "alive"
        assert "grace" in result.detail.lower()

    @patch("opencode_teams.spawner.capture_pane_content_hash")
    @patch("opencode_teams.spawner.check_pane_alive")
    def test_unknown_when_capture_fails(
        self, mock_alive: MagicMock, mock_hash: MagicMock
    ) -> None:
        mock_alive.return_value = True
        mock_hash.return_value = None
        member = _make_opencode_member(name="worker", prompt="Do work")
        member.joined_at = int(time.time() * 1000) - 120_000
        member.tmux_pane_id = "%42"
        result = check_single_agent_health(member, None, None)
        assert result.status == "unknown"

    @patch("opencode_teams.spawner.capture_pane_content_hash")
    @patch("opencode_teams.spawner.check_pane_alive")
    def test_alive_when_content_unchanged_within_timeout(
        self, mock_alive: MagicMock, mock_hash: MagicMock
    ) -> None:
        mock_alive.return_value = True
        mock_hash.return_value = "samehash"
        member = _make_opencode_member(name="worker", prompt="Do work")
        member.joined_at = int(time.time() * 1000) - 120_000
        member.tmux_pane_id = "%42"
        # Only 30s elapsed -- below 120s threshold
        result = check_single_agent_health(
            member, "samehash", time.time() - 30
        )
        assert result.status == "alive"


class TestHealthStatePersistence:
    def test_load_empty_state_when_no_file(self, team_dir: Path) -> None:
        result = load_health_state(TEAM, base_dir=team_dir)
        assert result == {}

    def test_save_and_load_round_trip(self, team_dir: Path) -> None:
        state = {
            "worker": {
                "hash": "abc123",
                "last_change_time": 1700000000.0,
            }
        }
        save_health_state(TEAM, state, base_dir=team_dir)
        loaded = load_health_state(TEAM, base_dir=team_dir)
        assert loaded["worker"]["hash"] == "abc123"
        assert loaded["worker"]["last_change_time"] == 1700000000.0

    def test_save_overwrites_previous(self, team_dir: Path) -> None:
        state1 = {"worker": {"hash": "old", "last_change_time": 1.0}}
        save_health_state(TEAM, state1, base_dir=team_dir)

        state2 = {"worker": {"hash": "new", "last_change_time": 2.0}}
        save_health_state(TEAM, state2, base_dir=team_dir)

        loaded = load_health_state(TEAM, base_dir=team_dir)
        assert loaded["worker"]["hash"] == "new"
        assert loaded["worker"]["last_change_time"] == 2.0


# Desktop app lifecycle tests


class TestDesktopDiscovery:
    def test_env_var_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_binary = tmp_path / "opencode-desktop"
        fake_binary.write_text("fake")
        monkeypatch.setenv(DESKTOP_BINARY_ENV_VAR, str(fake_binary))
        result = discover_desktop_binary()
        assert result == str(fake_binary)

    def test_env_var_override_missing_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(DESKTOP_BINARY_ENV_VAR, "/nonexistent/path/opencode-desktop")
        with pytest.raises(FileNotFoundError, match="does not exist"):
            discover_desktop_binary()

    def test_known_path_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_binary = tmp_path / "opencode-desktop"
        fake_binary.write_text("fake")
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(
            "opencode_teams.spawner.DESKTOP_PATHS",
            {"linux": [str(fake_binary)]},
        )
        monkeypatch.delenv(DESKTOP_BINARY_ENV_VAR, raising=False)
        result = discover_desktop_binary()
        assert result == str(fake_binary)

    def test_path_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("opencode_teams.spawner.DESKTOP_PATHS", {"linux": []})
        monkeypatch.setattr(
            "opencode_teams.spawner.shutil.which",
            lambda name: "/usr/local/bin/opencode-desktop" if name == "opencode-desktop" else None,
        )
        monkeypatch.delenv(DESKTOP_BINARY_ENV_VAR, raising=False)
        result = discover_desktop_binary()
        assert result == "/usr/local/bin/opencode-desktop"

    def test_not_found_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("opencode_teams.spawner.DESKTOP_PATHS", {"linux": []})
        monkeypatch.setattr("opencode_teams.spawner.shutil.which", lambda name: None)
        monkeypatch.delenv(DESKTOP_BINARY_ENV_VAR, raising=False)
        with pytest.raises(FileNotFoundError, match="Could not find OpenCode Desktop"):
            discover_desktop_binary()


class TestDesktopLaunch:
    def test_launch_returns_pid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_popen = MagicMock()
        mock_popen.pid = 12345
        mock_popen_cls = MagicMock(return_value=mock_popen)
        monkeypatch.setattr("opencode_teams.spawner.subprocess.Popen", mock_popen_cls)
        monkeypatch.setattr(sys, "platform", "linux")

        result = launch_desktop_app("/usr/bin/opencode-desktop", "/tmp/project")
        assert result == 12345
        mock_popen_cls.assert_called_once_with(
            ["/usr/bin/opencode-desktop"],
            cwd="/tmp/project",
            start_new_session=True,
        )

    def test_launch_windows_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_popen = MagicMock()
        mock_popen.pid = 99999
        mock_popen_cls = MagicMock(return_value=mock_popen)
        monkeypatch.setattr("opencode_teams.spawner.subprocess.Popen", mock_popen_cls)
        monkeypatch.setattr(sys, "platform", "win32")

        result = launch_desktop_app("/usr/bin/opencode-desktop", "/tmp/project")
        assert result == 99999
        call_kwargs = mock_popen_cls.call_args[1]
        expected_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        assert call_kwargs["creationflags"] == expected_flags
        assert "start_new_session" not in call_kwargs


class TestProcessLifecycle:
    def test_check_alive_with_running_process(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("opencode_teams.spawner.os.kill", lambda pid, sig: None)
        assert check_process_alive(1234) is True

    def test_check_alive_with_dead_process(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def raise_os_error(pid: int, sig: int) -> None:
            raise OSError("No such process")
        monkeypatch.setattr("opencode_teams.spawner.os.kill", raise_os_error)
        assert check_process_alive(1234) is False

    def test_check_alive_with_zero_pid(self) -> None:
        assert check_process_alive(0) is False

    def test_check_alive_with_negative_pid(self) -> None:
        assert check_process_alive(-1) is False

    def test_kill_desktop_process(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_kill = MagicMock()
        monkeypatch.setattr("opencode_teams.spawner.os.kill", mock_kill)
        kill_desktop_process(5678)
        mock_kill.assert_called_once_with(5678, signal.SIGTERM)

    def test_kill_desktop_process_already_dead(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def raise_os_error(pid: int, sig: int) -> None:
            raise OSError("No such process")
        monkeypatch.setattr("opencode_teams.spawner.os.kill", raise_os_error)
        # Should not raise
        kill_desktop_process(5678)

    def test_kill_desktop_process_zero_pid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_kill = MagicMock()
        monkeypatch.setattr("opencode_teams.spawner.os.kill", mock_kill)
        kill_desktop_process(0)
        mock_kill.assert_not_called()


class TestSpawnDesktopBackend:
    @patch("opencode_teams.spawner.launch_desktop_app", return_value=9999)
    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_desktop_calls_launch_desktop_app(
        self, mock_subprocess: MagicMock, mock_launch: MagicMock,
        tmp_base_dir: Path, tmp_path: Path,
    ) -> None:
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        member = spawn_teammate(
            TEAM, "desktop-agent", "Do work",
            "/usr/local/bin/opencode",
            backend_type="desktop",
            desktop_binary="/fake/opencode-desktop",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
        )
        mock_launch.assert_called_once()
        assert mock_launch.call_args[0][0] == "/fake/opencode-desktop"
        assert member.process_id == 9999
        assert member.backend_type == "desktop"

    def test_spawn_desktop_requires_desktop_binary(
        self, tmp_base_dir: Path, tmp_path: Path,
    ) -> None:
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        with pytest.raises(ValueError, match="desktop_binary is required"):
            spawn_teammate(
                TEAM, "desktop-agent", "Do work",
                "/usr/local/bin/opencode",
                backend_type="desktop",
                base_dir=tmp_base_dir,
                project_dir=project_dir,
            )

    @patch("opencode_teams.spawner.launch_desktop_app", return_value=8888)
    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_desktop_stores_pid_in_config(
        self, mock_subprocess: MagicMock, mock_launch: MagicMock,
        tmp_base_dir: Path, tmp_path: Path,
    ) -> None:
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spawn_teammate(
            TEAM, "desktop-agent", "Do work",
            "/usr/local/bin/opencode",
            backend_type="desktop",
            desktop_binary="/fake/opencode-desktop",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
        )
        config = teams.read_config(TEAM, base_dir=tmp_base_dir)
        found = [m for m in config.members if isinstance(m, TeammateMember) and m.name == "desktop-agent"]
        assert len(found) == 1
        assert found[0].process_id == 8888
        assert found[0].backend_type == "desktop"

    @patch("opencode_teams.spawner.subprocess")
    def test_spawn_tmux_still_works(
        self, mock_subprocess: MagicMock,
        tmp_base_dir: Path, tmp_path: Path,
    ) -> None:
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mock_subprocess.run.return_value.stdout = "%42\n"
        member = spawn_teammate(
            TEAM, "tmux-agent", "Do work",
            "/usr/local/bin/opencode",
            backend_type="tmux",
            base_dir=tmp_base_dir,
            project_dir=project_dir,
        )
        mock_subprocess.run.assert_called_once()
        call_args = mock_subprocess.run.call_args[0][0]
        assert "tmux" in call_args[0]
        assert member.tmux_pane_id == "%42"
        assert member.backend_type == "tmux"


class TestDesktopHealthCheck:
    def test_desktop_alive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        member = TeammateMember(
            agent_id="agent@team", name="agent", agent_type="general-purpose",
            model="kimi-k2.5", prompt="work", color="blue", joined_at=0,
            tmux_pane_id="", cwd="/tmp", backend_type="desktop", process_id=1234,
        )
        monkeypatch.setattr("opencode_teams.spawner.check_process_alive", lambda pid: True)
        result = check_single_agent_health(member, None, None)
        assert result.status == "alive"
        assert "running" in result.detail

    def test_desktop_dead(self, monkeypatch: pytest.MonkeyPatch) -> None:
        member = TeammateMember(
            agent_id="agent@team", name="agent", agent_type="general-purpose",
            model="kimi-k2.5", prompt="work", color="blue", joined_at=0,
            tmux_pane_id="", cwd="/tmp", backend_type="desktop", process_id=1234,
        )
        monkeypatch.setattr("opencode_teams.spawner.check_process_alive", lambda pid: False)
        result = check_single_agent_health(member, None, None)
        assert result.status == "dead"
        assert "no longer running" in result.detail

    def test_desktop_never_reports_hung(self, monkeypatch: pytest.MonkeyPatch) -> None:
        member = TeammateMember(
            agent_id="agent@team", name="agent", agent_type="general-purpose",
            model="kimi-k2.5", prompt="work", color="blue", joined_at=0,
            tmux_pane_id="", cwd="/tmp", backend_type="desktop", process_id=1234,
        )
        monkeypatch.setattr("opencode_teams.spawner.check_process_alive", lambda pid: True)
        # Simulate conditions that would trigger "hung" for tmux backend
        result = check_single_agent_health(
            member, "samehash", time.time() - 300, hung_timeout=120,
        )
        assert result.status == "alive"
        assert result.status != "hung"


class TestSpawnRollbackCleansConfig:
    """Verify that spawn_teammate rollback cleans up agent config on failure."""

    @patch("opencode_teams.spawner.subprocess")
    def test_rollback_removes_agent_config_on_tmux_failure(
        self, mock_subprocess: MagicMock, tmp_base_dir: Path, tmp_path: Path,
    ) -> None:
        teams.create_team(TEAM, session_id=SESSION_ID, base_dir=tmp_base_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Make tmux spawn fail
        mock_subprocess.run.side_effect = RuntimeError("tmux crashed")

        with pytest.raises(RuntimeError, match="tmux crashed"):
            spawn_teammate(
                TEAM, "fail-agent", "Do work",
                "/usr/local/bin/opencode",
                base_dir=tmp_base_dir,
                project_dir=project_dir,
            )

        # Agent config should have been cleaned up during rollback
        config_file = project_dir / ".opencode" / "agents" / "fail-agent.md"
        assert not config_file.exists()

        # Member should also have been removed from team config
        config = teams.read_config(TEAM, base_dir=tmp_base_dir)
        names = [m.name for m in config.members]
        assert "fail-agent" not in names


class TestCleanupAgentConfigReExport:
    """Verify cleanup_agent_config is importable from spawner (backward compat)."""

    def test_importable_from_spawner(self) -> None:
        assert callable(cleanup_agent_config)

    def test_removes_file(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / ".opencode" / "agents"
        agents_dir.mkdir(parents=True)
        config_file = agents_dir / "test-agent.md"
        config_file.write_text("# Test config")

        cleanup_agent_config(tmp_path, "test-agent")

        assert not config_file.exists()


class TestBuildWindowsTerminalCommand:
    """Tests for build_windows_terminal_command using -EncodedCommand."""

    def test_uses_encoded_command_not_command(self) -> None:
        member = _make_opencode_member()
        cmd = build_windows_terminal_command(member, "C:\\bin\\opencode.exe")
        assert "-EncodedCommand" in cmd
        assert "-Command" not in cmd

    def test_command_starts_with_powershell(self) -> None:
        member = _make_opencode_member()
        cmd = build_windows_terminal_command(member, "C:\\bin\\opencode.exe")
        assert cmd[0] == "powershell.exe"
        assert "-NoProfile" in cmd
        assert "-ExecutionPolicy" in cmd
        assert "Bypass" in cmd

    def test_encoded_script_decodes_to_expected_content(self) -> None:
        import base64
        member = _make_opencode_member(
            name="researcher", model="moonshot-ai/kimi-k2.5",
            cwd="/tmp", prompt="Do research",
        )
        cmd = build_windows_terminal_command(member, "/usr/local/bin/opencode")
        encoded_idx = cmd.index("-EncodedCommand") + 1
        encoded = cmd[encoded_idx]

        # Decode: Base64 → UTF-16LE → str
        script = base64.b64decode(encoded).decode("utf-16-le")

        # Verify key parts of the script
        assert "Set-Location -Path '/tmp'" in script
        assert "OpenCode Agent: researcher" in script
        assert "'/usr/local/bin/opencode' run" in script
        assert "--agent 'researcher'" in script
        assert "--model 'moonshot-ai/kimi-k2.5'" in script
        assert "'Do research'" in script
        assert "ReadKey" in script

    def test_prompt_with_single_quotes_escaped(self) -> None:
        import base64
        member = _make_opencode_member(prompt="Fix 'main.py' bugs")
        cmd = build_windows_terminal_command(member, "/usr/local/bin/opencode")
        encoded_idx = cmd.index("-EncodedCommand") + 1
        script = base64.b64decode(cmd[encoded_idx]).decode("utf-16-le")

        # Single quotes should be doubled for PS single-quoted strings
        assert "'Fix ''main.py'' bugs'" in script

    def test_prompt_with_double_quotes(self) -> None:
        import base64
        member = _make_opencode_member(prompt='Use "$HOME" variable')
        cmd = build_windows_terminal_command(member, "/usr/local/bin/opencode")
        encoded_idx = cmd.index("-EncodedCommand") + 1
        script = base64.b64decode(cmd[encoded_idx]).decode("utf-16-le")

        # Double quotes should pass through untouched (inside single-quoted PS string)
        assert '"$HOME"' in script

    def test_prompt_with_newlines(self) -> None:
        import base64
        member = _make_opencode_member(prompt="Line 1\nLine 2\nLine 3")
        cmd = build_windows_terminal_command(member, "/usr/local/bin/opencode")
        encoded_idx = cmd.index("-EncodedCommand") + 1
        script = base64.b64decode(cmd[encoded_idx]).decode("utf-16-le")

        # Newlines should be preserved in the encoded script
        assert "Line 1\nLine 2\nLine 3" in script

    def test_cwd_with_spaces_escaped(self) -> None:
        import base64
        member = _make_opencode_member(cwd="C:\\Users\\John Doe\\Projects")
        cmd = build_windows_terminal_command(member, "/usr/local/bin/opencode")
        encoded_idx = cmd.index("-EncodedCommand") + 1
        script = base64.b64decode(cmd[encoded_idx]).decode("utf-16-le")

        assert "C:\\Users\\John Doe\\Projects" in script
