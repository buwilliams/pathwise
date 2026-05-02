from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def render_template(template_path: Path, context: dict[str, Any]) -> str:
    """Render a Jinja2 markdown template from a file path.

    StrictUndefined catches missing context keys at render time rather than
    silently producing the empty string — much easier to debug bad prompts.
    """
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = env.get_template(template_path.name)
    return template.render(**context)


def render_string(template_str: str, context: dict[str, Any]) -> str:
    env = Environment(undefined=StrictUndefined, keep_trailing_newline=True)
    return env.from_string(template_str).render(**context)
