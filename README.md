# Pathwise

*One step at a time, on purpose.*

A life-strategy planner for teens. Pathwise turns a formal life-state model into a mobile-first web app, REST API, and CLI that helps young people think through big transitions — like graduating, getting a car, moving out, or picking what to learn next.

## Origin

Pathwise grew out of the essay [**Emma: Build Independence**](https://github.com/buwilliams/buddy-williams-writings/blob/main/fragments/emma-build-independence.md). The current, in-repo source-of-truth for any season's model lives at `src/pathwise/seasons/{season}/revisions/{revision}/model.md` — a formalized conjecture for that revision. The essay is the wisdom; this repo is the software that makes it usable.

## Concepts

- **Season** — a life chapter the planner is built for. Each season has its own questions, scenarios, scoring weights, and prompts. Today: `build-independence` (ages 17–20). Later: marriage, kids, complex finances.
- **Revision** — a versioned snapshot of a season under `revisions/v<X>_<Y>_<Z>/`. The revision directory is self-contained: `pack.toml`, `questionnaire.json`, `weights.yaml`, `scenarios.yaml`, `prompts/*.md`, `model.md`, and a `logic.py`. New plans always use the latest revision; existing user data stays pinned to whichever revision produced it.
- **Model** (`model.md`) — the formalized conjecture for that revision. Math, definitions, and tradeoffs. The deterministic core (`life_state.py`, `momentum.py`) operationalizes it.
- **Questionnaire** (`questionnaire.json`) — a JSON schema with three concerns kept separate: `data_model` (durable contract with the core), `questions` (prompt + UI presentation per field), and `steps` (ordered groups for the wizard). `when` predicates conditionally hide steps and questions based on prior answers. The frontend renders the wizard entirely from this schema.

## What's here

- **Deterministic core** (`src/pathwise/core/`) — pure-Python math for life-state, viability, momentum, fragility; predicate evaluator; questionnaire schema and service.
- **Season packs** (`src/pathwise/seasons/`) — one directory per season; revisions live under it.
- **LLM layer** (`src/pathwise/llm/`) — Claude does grounded research (`web_search`) and final plan synthesis.
- **Surfaces** — FastAPI (`src/pathwise/api/`), Typer CLI (`src/pathwise/cli/`), vanilla ES6 frontend (`src/pathwise/frontend/`), SMS via Twilio (`src/pathwise/sms/`).

## Stack

Python 3.12+, uv, FastAPI, Pydantic, Typer, Anthropic SDK, Twilio, Jinja2, PyYAML. Tests via pytest.

## Getting started

```bash
uv sync                          # install runtime deps
uv pip install -e .              # editable install (needed for pytest to find the package)
uv run pathwise --help           # CLI overview
uv run pathwise serve --reload   # FastAPI + uvicorn on the configured host/port
uv run pytest                    # full test suite
```

The CLI groups commands by area: `pathwise user|auth|season|question|answer|plan ...`. Run any group with `--help` to see what's there. To inspect the live questionnaire schema for a season:

```bash
uv run pathwise season show build-independence
uv run pathwise question list
```
