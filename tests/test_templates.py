from __future__ import annotations

import pytest

from opencode_teams.templates import (
    TEMPLATES,
    AgentTemplate,
    get_template,
    list_templates,
)


class TestTemplateRegistry:
    """Tests for the template registry: AgentTemplate dataclass, TEMPLATES dict, helpers."""

    def test_has_four_required_templates(self) -> None:
        required = {"researcher", "implementer", "reviewer", "tester"}
        assert required.issubset(TEMPLATES.keys())

    def test_all_templates_are_agent_template_instances(self) -> None:
        for name, template in TEMPLATES.items():
            assert isinstance(template, AgentTemplate), f"{name} is not AgentTemplate"

    def test_all_templates_have_nonempty_role_instructions(self) -> None:
        for name, template in TEMPLATES.items():
            assert len(template.role_instructions.strip()) > 0, (
                f"{name} has empty role_instructions"
            )

    def test_all_templates_have_nonempty_description(self) -> None:
        for name, template in TEMPLATES.items():
            assert len(template.description.strip()) > 0, (
                f"{name} has empty description"
            )

    def test_get_template_returns_template(self) -> None:
        tmpl = get_template("researcher")
        assert tmpl is not None
        assert isinstance(tmpl, AgentTemplate)
        assert tmpl.name == "researcher"

    def test_get_template_returns_none_for_unknown(self) -> None:
        assert get_template("nonexistent") is None

    def test_list_templates_returns_all(self) -> None:
        result = list_templates()
        assert len(result) >= 4
        for entry in result:
            assert "name" in entry
            assert "description" in entry

    def test_templates_are_frozen(self) -> None:
        tmpl = get_template("researcher")
        assert tmpl is not None
        with pytest.raises(AttributeError):
            tmpl.name = "hacked"  # type: ignore[misc]

    def test_role_instructions_contain_role_heading(self) -> None:
        for name, template in TEMPLATES.items():
            assert "# Role:" in template.role_instructions, (
                f"{name} missing '# Role:' heading"
            )

    def test_tool_overrides_empty_for_v1(self) -> None:
        for name, template in TEMPLATES.items():
            assert template.tool_overrides == {}, (
                f"{name} has non-empty tool_overrides"
            )
