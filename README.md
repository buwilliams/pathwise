# Pathwise

*One step at a time, on purpose.*

A life-strategy planner for teens. Pathwise turns a formal life-state model into a mobile-first web app, REST API, and CLI that helps young people think through big transitions — like graduating, getting a car, moving out, or picking what to learn next.

## Origin

Pathwise is built on the essay [**Emma: Build Independence**](https://github.com/buwilliams/buddy-williams-writings/blob/main/fragments/emma-build-independence.md) — a formal model of life-state `L = {V, T, M, Y, K}` with viability, momentum, and fragility math, and an "independence ladder" conjecture. The essay is the source of truth for the wisdom; this repo is the software that makes it usable.

## What's here

- **Deterministic core** (`src/pathwise/core/`) — pure-Python math for life-state, viability, momentum, fragility.
- **Season packs** (`src/pathwise/seasons/`) — pluggable wisdom for a particular life chapter. Each season is versioned by *revision* under `revisions/<rev>/`; new plans always use the latest revision, while existing user data stays pinned to whichever revision produced it. Today: `build_independence`. Later: marriage, kids, complex finances.
- **LLM layer** (`src/pathwise/llm/`) — Claude does grounded research (`web_search`) and final plan synthesis.
- **Surfaces** — FastAPI (`api/`), Typer CLI (`cli/`), vanilla ES6 frontend (`frontend/`), SMS via Twilio (`sms/`).

## Stack

Python 3.12+, uv, FastAPI, Typer, Anthropic SDK, Twilio, Jinja2, Pydantic.

## Getting started

```bash
uv sync
uv run pathwise --help
uv run uvicorn pathwise.api.main:app --reload
uv run pytest
```
