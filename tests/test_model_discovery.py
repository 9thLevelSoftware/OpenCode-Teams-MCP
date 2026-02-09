"""Tests for OpenCode model discovery and selection."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from opencode_teams.model_discovery import (
    discover_models,
    load_opencode_config,
    resolve_model_string,
    select_model_by_preference,
)
from opencode_teams.models import ModelInfo, ModelPreference


class TestLoadOpencodeConfig:
    """Tests for loading and merging OpenCode configuration."""

    def test_returns_empty_when_no_configs(self, tmp_path: Path) -> None:
        """Returns empty dict when no config files exist."""
        # Point to non-existent paths
        result = load_opencode_config(tmp_path / "nonexistent")
        # Should return whatever global config exists (if any) or empty-ish
        assert isinstance(result, dict)

    def test_loads_project_config(self, tmp_path: Path) -> None:
        """Loads config from project opencode.json."""
        config = {
            "provider": {
                "test-provider": {
                    "models": {"test-model": {"name": "Test Model"}}
                }
            }
        }
        config_path = tmp_path / "opencode.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = load_opencode_config(tmp_path)
        assert "provider" in result
        assert "test-provider" in result["provider"]

    def test_handles_malformed_json(self, tmp_path: Path) -> None:
        """Handles malformed JSON gracefully."""
        config_path = tmp_path / "opencode.json"
        config_path.write_text("not valid json {{{", encoding="utf-8")

        result = load_opencode_config(tmp_path)
        # Should not crash, just return whatever was loaded from global
        assert isinstance(result, dict)


class TestDiscoverModels:
    """Tests for model discovery from config."""

    def test_empty_config(self) -> None:
        """Returns empty list for empty config."""
        assert discover_models({}) == []
        assert discover_models({"provider": {}}) == []

    def test_single_model(self) -> None:
        """Discovers a single model correctly."""
        config = {
            "provider": {
                "openai": {
                    "models": {
                        "gpt-5.2-medium": {
                            "name": "GPT 5.2 Medium",
                            "limit": {"context": 272000, "output": 128000},
                            "modalities": {
                                "input": ["text", "image"],
                                "output": ["text"],
                            },
                            "options": {"reasoningEffort": "medium"},
                        }
                    }
                }
            }
        }
        models = discover_models(config)
        assert len(models) == 1
        m = models[0]
        assert m.provider == "openai"
        assert m.model_id == "gpt-5.2-medium"
        assert m.name == "GPT 5.2 Medium"
        assert m.full_model_string == "openai/gpt-5.2-medium"
        assert m.context_window == 272000
        assert m.max_output == 128000
        assert m.input_modalities == ["text", "image"]
        assert m.output_modalities == ["text"]
        assert m.reasoning_effort == "medium"

    def test_multiple_providers(self) -> None:
        """Discovers models from multiple providers."""
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

    def test_multiple_models_per_provider(self) -> None:
        """Discovers multiple models from same provider."""
        config = {
            "provider": {
                "openai": {
                    "models": {
                        "gpt-5-low": {"name": "GPT 5 Low"},
                        "gpt-5-high": {"name": "GPT 5 High"},
                    }
                }
            }
        }
        models = discover_models(config)
        assert len(models) == 2

    def test_inherits_provider_reasoning_effort(self) -> None:
        """Model without options inherits provider-level reasoning effort."""
        config = {
            "provider": {
                "openai": {
                    "options": {"reasoningEffort": "high"},
                    "models": {"gpt-5": {"name": "GPT 5"}},
                }
            }
        }
        models = discover_models(config)
        assert models[0].reasoning_effort == "high"

    def test_model_reasoning_overrides_provider(self) -> None:
        """Model-level reasoning effort overrides provider-level."""
        config = {
            "provider": {
                "openai": {
                    "options": {"reasoningEffort": "high"},
                    "models": {
                        "gpt-5": {
                            "name": "GPT 5",
                            "options": {"reasoningEffort": "low"},
                        }
                    },
                }
            }
        }
        models = discover_models(config)
        assert models[0].reasoning_effort == "low"

    def test_handles_missing_optional_fields(self) -> None:
        """Handles models with missing optional fields."""
        config = {
            "provider": {
                "minimal": {
                    "models": {"m1": {"name": "Minimal Model"}}
                }
            }
        }
        models = discover_models(config)
        assert len(models) == 1
        m = models[0]
        assert m.context_window == 0
        assert m.max_output == 0
        assert m.input_modalities == ["text"]
        assert m.reasoning_effort is None


class TestSelectModelByPreference:
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

    def test_empty_models_returns_none(self) -> None:
        """Returns None for empty model list."""
        pref = ModelPreference()
        assert select_model_by_preference([], pref) is None

    def test_no_preference_returns_highest_scored(self, sample_models: list[ModelInfo]) -> None:
        """With no preference, returns model with best overall score."""
        pref = ModelPreference()
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        # Gemini has highest context window, should score high
        assert selected.context_window > 0

    def test_filter_by_provider(self, sample_models: list[ModelInfo]) -> None:
        """Filters to only models from specified provider."""
        pref = ModelPreference(provider="google")
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        assert selected.provider == "google"

    def test_filter_by_min_context(self, sample_models: list[ModelInfo]) -> None:
        """Filters to models meeting minimum context window."""
        pref = ModelPreference(min_context_window=500000)
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        assert selected.context_window >= 500000
        assert selected.provider == "google"  # Only Gemini meets this

    def test_filter_by_modalities(self, sample_models: list[ModelInfo]) -> None:
        """Filters to models supporting required modalities."""
        pref = ModelPreference(required_modalities=["pdf"])
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        assert "pdf" in selected.input_modalities

    def test_prefer_reasoning_effort(self, sample_models: list[ModelInfo]) -> None:
        """Prefers models matching reasoning effort."""
        pref = ModelPreference(reasoning_effort="high")
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        assert selected.reasoning_effort == "high"

    def test_prefer_speed(self, sample_models: list[ModelInfo]) -> None:
        """Prefers faster (lower reasoning) models when prefer_speed is True."""
        pref = ModelPreference(prefer_speed=True)
        selected = select_model_by_preference(sample_models, pref)
        assert selected is not None
        # Should prefer low reasoning or None over high
        assert selected.reasoning_effort in ("low", None)

    def test_no_match_returns_none(self, sample_models: list[ModelInfo]) -> None:
        """Returns None when no models match constraints."""
        pref = ModelPreference(provider="anthropic")  # Not in sample
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
            ),
            ModelInfo(
                provider="google",
                model_id="gemini-3-flash",
                name="Gemini 3 Flash",
                full_model_string="google/gemini-3-flash",
                context_window=1048576,
            ),
        ]

    def test_passthrough_full_string(self, sample_models: list[ModelInfo]) -> None:
        """Full provider/model strings pass through unchanged."""
        result = resolve_model_string("openai/gpt-5.2-medium", sample_models)
        assert result == "openai/gpt-5.2-medium"

    def test_passthrough_arbitrary_full_string(self, sample_models: list[ModelInfo]) -> None:
        """Arbitrary full strings pass through even if not in models list."""
        result = resolve_model_string("custom/my-model", sample_models)
        assert result == "custom/my-model"

    def test_resolve_by_model_id(self, sample_models: list[ModelInfo]) -> None:
        """Model IDs are resolved to full provider/model strings."""
        result = resolve_model_string("gpt-5.2-medium", sample_models)
        assert result == "openai/gpt-5.2-medium"

    def test_resolve_by_model_id_different_provider(self, sample_models: list[ModelInfo]) -> None:
        """Resolves model ID from any provider."""
        result = resolve_model_string("gemini-3-flash", sample_models)
        assert result == "google/gemini-3-flash"

    def test_auto_selects_model(self, sample_models: list[ModelInfo]) -> None:
        """'auto' selects a model based on preferences."""
        result = resolve_model_string("auto", sample_models)
        # Should return one of the available models
        assert "/" in result

    def test_auto_with_preference(self, sample_models: list[ModelInfo]) -> None:
        """'auto' respects preference constraints."""
        pref = ModelPreference(provider="google")
        result = resolve_model_string("auto", sample_models, pref)
        assert result == "google/gemini-3-flash"

    def test_unknown_model_passthrough(self, sample_models: list[ModelInfo]) -> None:
        """Unknown model IDs pass through for OpenCode to validate."""
        result = resolve_model_string("unknown-model", sample_models)
        assert result == "unknown-model"

    def test_auto_with_no_models_raises(self) -> None:
        """'auto' with no models raises ValueError."""
        with pytest.raises(ValueError, match="No models available"):
            resolve_model_string("auto", [])
