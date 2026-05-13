"""Interactive path sandbox — the math as the surface, not the LLM.

Three endpoints power the sandbox view:

* ``GET  /seasons/{id}/sandbox`` — the opening hand. Baseline life-state,
  the season pack's paths-of-stages config (durations, recoverability inputs,
  flags), and the default ``SandboxConfig`` the UI should render its sliders
  from.
* ``POST /seasons/{id}/sandbox/simulate`` — recompute after the user moves a
  slider. The body is whatever ``parse_config`` accepts; the response is a
  ``SandboxResult`` JSON.
* ``POST /seasons/{id}/sandbox/narrate`` — given the user's current config
  and result, ask the LLM to narrate what *they* found. The LLM is
  downstream of the math; it doesn't pick the answer.

The user must have a profile and the questionnaire must be complete enough
to derive a baseline life-state. We reuse the same ``QuestionnaireService``
the plan endpoint uses so the same incompleteness UX kicks in.
"""

from __future__ import annotations

from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pathwise.api.deps import CurrentUserId, StoreDep
from pathwise.config import get_settings
from pathwise.core.plan import QuestionnaireIncomplete
from pathwise.core.profile import ProfileService
from pathwise.core.questionnaire import QuestionnaireService
from pathwise.core.sandbox import (
    initial_config,
    parse_config,
    result_to_json,
    simulate,
)
from pathwise.core.season import get_pack
from pathwise.llm.narrate import narrate_discovery

router = APIRouter(prefix="/seasons/{season_id}/sandbox", tags=["sandbox"])


class SimulateRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class NarrateRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)
    # Optional one-line user prompt describing what they want narrated.
    # Examples: "What just happened when I dropped rho to 0?", "Why did the
    # train_then_work path go red?", "Compare the two paths on the Pareto
    # frontier." If empty, the LLM is told to summarize the most surprising
    # finding visible in the current config.
    focus: str | None = None


def _paths_raw_for(pack: Any) -> list[dict[str, Any]]:
    """Load the raw paths config straight from the revision's yaml — this is
    the same data the v0_5_0 logic reads. We need the raw dicts (with stage
    ids, durations, recoverability sub-inputs) for the simulator."""
    scenarios_path = pack.pack_dir / "scenarios.yaml"
    raw = yaml.safe_load(scenarios_path.read_text())
    return raw.get("paths", [])


def _horizon_for(pack: Any) -> int:
    scenarios_path = pack.pack_dir / "scenarios.yaml"
    raw = yaml.safe_load(scenarios_path.read_text())
    return int(raw.get("horizon_months", 60))


def _rec_weights_for(pack: Any) -> dict[str, float]:
    weights_path = pack.pack_dir / "weights.yaml"
    raw = yaml.safe_load(weights_path.read_text())
    return raw.get("recoverability_weights", {}) or {}


def _baseline_life(user_id: str, season_id: str, store: Any) -> Any:
    """Derive the baseline L the sandbox simulates from. Lifts the
    same precondition the plan endpoint uses: questionnaire complete."""
    profile = ProfileService(store).get(user_id)
    if profile is None:
        raise HTTPException(status_code=400, detail="No profile for user.")
    pack = get_pack(season_id)
    qs = QuestionnaireService(store)
    answers = qs.get_answers(user_id, pack.id)
    completion = qs.completion(user_id, pack)
    if not completion.is_complete:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "questionnaire_incomplete",
                "message": "Finish the questionnaire to use the sandbox.",
                "missing_required": completion.missing_required,
            },
        )
    return profile, pack, answers, pack.logic.compute_life_state(answers)


def _path_meta(paths_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """JSON-safe summary of the static path config the UI needs to render
    its initial sliders: stage labels, default durations, recoverability
    inputs (so the user can see what each stage is committing to)."""
    out: list[dict[str, Any]] = []
    for p in paths_raw:
        out.append(
            {
                "id": p["id"],
                "label": p["label"],
                "description": p.get("description", ""),
                "bucket": p.get("bucket", "skill_leverage"),
                "stages": [
                    {
                        "id": s["id"],
                        "label": s["label"],
                        "duration_months": float(s.get("duration_months", 0)),
                        "training_active": bool(s.get("training_active")),
                        "moves_out": bool(s.get("moves_out")),
                        "car": bool(s.get("car")),
                        "income_growth": bool(s.get("income_growth")),
                        "recoverability": s.get("recoverability") or {},
                    }
                    for s in p.get("stages", [])
                ],
            }
        )
    return out


@router.get("")
def show(season_id: str, store: StoreDep, user_id: CurrentUserId) -> dict[str, Any]:
    """Initial sandbox state — baseline, paths config, default sliders, and
    the first deterministic simulation."""
    try:
        profile, pack, answers, base = _baseline_life(user_id, season_id, store)
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    paths_raw = _paths_raw_for(pack)
    horizon = _horizon_for(pack)
    rec_weights = _rec_weights_for(pack)
    config = initial_config(paths_raw, base)
    result = simulate(
        paths_raw=paths_raw,
        base=base,
        weights=pack.weights,
        rec_weights=rec_weights,
        horizon_months=horizon,
        config=config,
    )
    return {
        "season_id": season_id,
        "season_name": pack.name,
        "pack_version": pack.version,
        "horizon_months": horizon,
        "baseline": pack.logic.life_state_to_meta(base),
        "paths_meta": _path_meta(paths_raw),
        "config": result.config_echo,
        "result": result_to_json(result),
    }


@router.post("/simulate")
def simulate_endpoint(
    season_id: str,
    req: SimulateRequest,
    store: StoreDep,
    user_id: CurrentUserId,
) -> dict[str, Any]:
    try:
        profile, pack, answers, base = _baseline_life(user_id, season_id, store)
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    paths_raw = _paths_raw_for(pack)
    horizon = _horizon_for(pack)
    rec_weights = _rec_weights_for(pack)
    config = parse_config(req.config)
    result = simulate(
        paths_raw=paths_raw,
        base=base,
        weights=pack.weights,
        rec_weights=rec_weights,
        horizon_months=horizon,
        config=config,
    )
    return {"result": result_to_json(result)}


@router.post("/narrate")
def narrate_endpoint(
    season_id: str,
    req: NarrateRequest,
    store: StoreDep,
    user_id: CurrentUserId,
) -> dict[str, Any]:
    """Ask the LLM to narrate what the user just did in the sandbox.

    The LLM gets the user's config (what they set the sliders to), the
    simulation result (what the math now says), and the user's optional
    focus question. It does NOT get to pick the answer — its job is to
    name the pattern the user revealed.
    """
    try:
        profile, pack, answers, base = _baseline_life(user_id, season_id, store)
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    paths_raw = _paths_raw_for(pack)
    horizon = _horizon_for(pack)
    rec_weights = _rec_weights_for(pack)
    config = parse_config(req.config)
    result = simulate(
        paths_raw=paths_raw,
        base=base,
        weights=pack.weights,
        rec_weights=rec_weights,
        horizon_months=horizon,
        config=config,
    )
    settings = get_settings()
    text = narrate_discovery(
        profile=profile,
        pack=pack,
        life_state_meta=pack.logic.life_state_to_meta(base),
        result_json=result_to_json(result),
        focus=req.focus,
        model=settings.pathwise_chat_model,
    )
    return {"narration": text}
