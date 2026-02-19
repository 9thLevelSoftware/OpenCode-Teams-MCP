"""OpenCode model discovery and selection.

Discovers models from OpenCode configuration files and provides preference-based
selection for spawning agents with appropriate models.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from opencode_teams.models import ModelInfo, ModelPreference


# Config file locations
def _get_global_config_path() -> Path:
    """Get the global OpenCode config path.

    On Windows: ~/.config/opencode/opencode.json
    On macOS/Linux: ~/.config/opencode/opencode.json
    """
    # XDG_CONFIG_HOME or fallback to ~/.config
    config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(config_home) / "opencode" / "opencode.json"


def _get_project_config_path(project_dir: Path | None = None) -> Path:
    """Get the project-level OpenCode config path.

    Project config is at <project_root>/opencode.json
    """
    root = project_dir or Path.cwd()
    return root / "opencode.json"


def load_opencode_config(project_dir: Path | None = None) -> dict[str, Any]:
    """Load and merge OpenCode configuration from global and project configs.

    Project config overrides global config (deep merge for providers).

    Args:
        project_dir: Project root directory. Defaults to cwd.

    Returns:
        Merged configuration dict. Empty dict if no configs found.
    """
    merged: dict[str, Any] = {}

    # Load global config first
    global_path = _get_global_config_path()
    if global_path.exists():
        try:
            global_config = json.loads(global_path.read_text(encoding="utf-8"))
            merged = global_config
        except (json.JSONDecodeError, OSError):
            pass  # Ignore malformed or unreadable config

    # Load and merge project config
    project_path = _get_project_config_path(project_dir)
    if project_path.exists():
        try:
            project_config = json.loads(project_path.read_text(encoding="utf-8"))
            # Deep merge providers
            if "provider" in project_config:
                merged.setdefault("provider", {})
                for provider_name, provider_config in project_config[
                    "provider"
                ].items():
                    if provider_name in merged["provider"]:
                        # Merge models
                        merged["provider"][provider_name].setdefault("models", {})
                        if "models" in provider_config:
                            merged["provider"][provider_name]["models"].update(
                                provider_config["models"]
                            )
                        # Merge other provider-level keys
                        for key, value in provider_config.items():
                            if key != "models":
                                merged["provider"][provider_name][key] = value
                    else:
                        merged["provider"][provider_name] = provider_config
            # Merge other top-level keys (project overrides)
            for key, value in project_config.items():
                if key != "provider":
                    merged[key] = value
        except (json.JSONDecodeError, OSError):
            pass  # Ignore malformed or unreadable config

    return merged


def _parse_reasoning_effort(
    options: dict[str, Any] | None,
) -> Literal["none", "low", "medium", "high", "xhigh"] | None:
    """Extract reasoning effort from model/provider options."""
    if not options:
        return None
    effort = options.get("reasoningEffort")
    if effort in ("none", "low", "medium", "high", "xhigh"):
        return effort
    return None


def discover_models(config: dict[str, Any] | None = None) -> list[ModelInfo]:
    """Discover all available models from OpenCode configuration.

    Parses provider.*.models.* entries and extracts capabilities.

    Args:
        config: Pre-loaded config dict. If None, loads from disk.

    Returns:
        List of ModelInfo objects for all discovered models.
    """
    if config is None:
        config = load_opencode_config()

    models: list[ModelInfo] = []
    providers = config.get("provider", {})

    for provider_name, provider_config in providers.items():
        if not isinstance(provider_config, dict):
            continue

        # Provider-level options (fallback for models without options)
        provider_options = provider_config.get("options", {})
        provider_reasoning = _parse_reasoning_effort(provider_options)

        provider_models = provider_config.get("models", {})
        if not isinstance(provider_models, dict):
            continue

        for model_id, model_config in provider_models.items():
            if not isinstance(model_config, dict):
                continue

            # Extract limits
            limits = model_config.get("limit", {})
            context_window = limits.get("context", 0)
            max_output = limits.get("output", 0)

            # Extract modalities
            modalities = model_config.get("modalities", {})
            input_modalities = modalities.get("input", ["text"])
            output_modalities = modalities.get("output", ["text"])

            # Extract reasoning effort (model-level overrides provider-level)
            model_options = model_config.get("options", {})
            reasoning_effort = (
                _parse_reasoning_effort(model_options) or provider_reasoning
            )

            # Build full model string
            full_model_string = f"{provider_name}/{model_id}"

            models.append(
                ModelInfo(
                    provider=provider_name,
                    model_id=model_id,
                    name=model_config.get("name", model_id),
                    full_model_string=full_model_string,
                    context_window=context_window,
                    max_output=max_output,
                    input_modalities=input_modalities,
                    output_modalities=output_modalities,
                    reasoning_effort=reasoning_effort,
                )
            )

    return models


def select_model_by_preference(
    models: list[ModelInfo],
    preference: ModelPreference,
) -> ModelInfo | None:
    """Select the best model matching the given preferences.

    Scoring algorithm:
    1. Filter by hard constraints (min_context_window, required_modalities)
    2. Score remaining models by preference match
    3. Return highest-scoring model

    Args:
        models: List of available models to choose from.
        preference: Selection criteria.

    Returns:
        Best matching ModelInfo, or None if no models match constraints.
    """
    if not models:
        return None

    candidates: list[tuple[int, ModelInfo]] = []

    for model in models:
        # Hard constraints
        if (
            preference.min_context_window
            and model.context_window < preference.min_context_window
        ):
            continue

        if preference.required_modalities:
            if not all(
                m in model.input_modalities for m in preference.required_modalities
            ):
                continue

        if preference.provider and model.provider != preference.provider:
            continue

        # Scoring
        score = 0

        # Reasoning effort match (exact match = 100, adjacent = 50)
        if preference.reasoning_effort and model.reasoning_effort:
            effort_levels = ["none", "low", "medium", "high", "xhigh"]
            try:
                pref_idx = effort_levels.index(preference.reasoning_effort)
                model_idx = effort_levels.index(model.reasoning_effort)
                distance = abs(pref_idx - model_idx)
                if distance == 0:
                    score += 100
                elif distance == 1:
                    score += 50
                # Distance > 1: no bonus
            except ValueError:
                pass  # Unknown effort level, skip scoring

        # Context window bonus (logarithmic, max 50 points)
        if model.context_window > 0:
            # 128k = ~17 log2, 1M = ~20 log2
            import math

            context_score = min(50, int(math.log2(model.context_window) * 2.5))
            score += context_score

        # Max output bonus (smaller weight)
        if model.max_output > 0:
            import math

            output_score = min(20, int(math.log2(model.max_output) * 1.5))
            score += output_score

        # Speed preference: lower reasoning = higher priority when speed matters
        if preference.prefer_speed and model.reasoning_effort:
            effort_levels = ["none", "low", "medium", "high", "xhigh"]
            try:
                model_idx = effort_levels.index(model.reasoning_effort)
                # Invert: none=40, low=30, medium=20, high=10, xhigh=0
                speed_score = (4 - model_idx) * 10
                score += max(0, speed_score)
            except ValueError:
                pass

        candidates.append((score, model))

    if not candidates:
        return None

    # Sort by score descending, return best
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def resolve_model_string(
    model: str,
    models: list[ModelInfo] | None = None,
    preference: ModelPreference | None = None,
) -> str:
    """Resolve a model alias or preference to a full provider/model string.

    Resolution order:
    1. If model is "auto", use preference-based selection
    2. If model contains "/", assume it's already a full provider/model string
    3. Otherwise, search for matching model_id across all providers

    Args:
        model: Model alias, model_id, or full provider/model string.
        models: List of available models (loads from config if None).
        preference: Selection preferences (used when model="auto").

    Returns:
        Full provider/model string (e.g., "openai/gpt-5.2", "openai/gpt-5.3-codex",
        "google/gemini-2.5-flash", "kimi-for-coding/k2p5").

    Raises:
        ValueError: If model cannot be resolved and no fallback is available.
    """
    if models is None:
        models = discover_models()

    # Case 1: auto selection
    if model == "auto":
        pref = preference or ModelPreference()
        selected = select_model_by_preference(models, pref)
        if selected:
            return selected.full_model_string
        # Fallback: first available model
        if models:
            return models[0].full_model_string
        raise ValueError("No models available. Configure providers in opencode.json.")

    # Case 2: already full provider/model string
    if "/" in model:
        return model

    # Case 3: search by model_id
    for m in models:
        if m.model_id == model:
            return m.full_model_string

    # Case 4: no match found - return as-is (OpenCode will validate)
    # This allows users to specify models not in config
    return model
