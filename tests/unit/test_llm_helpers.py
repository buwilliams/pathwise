from __future__ import annotations

from pathlib import Path

from pathwise.llm.research import _extract_json
from pathwise.llm.templates import render_string, render_template


class TestExtractJson:
    def test_plain_object(self) -> None:
        assert _extract_json('{"a": 1, "b": 2}') == {"a": 1, "b": 2}

    def test_fenced(self) -> None:
        text = "Here you go:\n```json\n{\"x\": 5}\n```\nDone."
        assert _extract_json(text) == {"x": 5}

    def test_with_prose_around(self) -> None:
        text = "Sure! Here is the data: {\"used_car\": {\"low\": 5000}} -- end"
        assert _extract_json(text) == {"used_car": {"low": 5000}}

    def test_nested_braces(self) -> None:
        assert _extract_json('{"a": {"b": {"c": 1}}, "d": 2}') == {
            "a": {"b": {"c": 1}},
            "d": 2,
        }

    def test_brace_inside_string(self) -> None:
        assert _extract_json('{"note": "use { carefully }", "ok": true}') == {
            "note": "use { carefully }",
            "ok": True,
        }

    def test_invalid_returns_empty(self) -> None:
        assert _extract_json("no json here at all") == {}
        assert _extract_json("{ broken json") == {}


class TestTemplates:
    def test_render_string_with_context(self) -> None:
        out = render_string("Hello {{ name }}!", {"name": "Emma"})
        assert out == "Hello Emma!"

    def test_render_string_strict_undefined_raises(self) -> None:
        from jinja2.exceptions import UndefinedError

        import pytest

        with pytest.raises(UndefinedError):
            render_string("Hi {{ missing }}", {})

    def test_render_template_from_file(self, tmp_path: Path) -> None:
        path = tmp_path / "x.md"
        path.write_text("# {{ greeting }} {{ profile.first_name }}")
        out = render_template(
            path, {"greeting": "Hello", "profile": type("P", (), {"first_name": "Emma"})}
        )
        assert "Hello Emma" in out
