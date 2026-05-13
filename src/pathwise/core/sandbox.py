"""Interactive path simulator.

The plan view ships a static markdown doc with one set of numbers baked in.
The sandbox is the inverse: the math is the surface. Users move the levers
(stage durations, completion risk ``rho``, technology trajectory ``delta``,
rent/car/training cost), watch the viability filter fail or pass, and see
the Pareto frontier of ``{path_momentum, R_min}`` shift across paths.

This module is the deterministic core for that. Three responsibilities:

1. Take a baseline life-state plus the season pack's paths-of-stages config,
   apply a user's overrides, and return one ``PathResult`` per path — same
   shape the plan template already consumes.
2. Compute the Pareto frontier across paths in
   ``{path_momentum, min_recoverability}`` space, both maximized.
3. Run Monte Carlo over the uncertain inputs the user marked as uncertain
   (rho, delta, rent, car overhead) and roll those samples up into per-path
   ``{p10, p50, p90}`` momentum and ``P(viable)``.

The LLM is downstream of this — see ``llm/narrate.py``. The user makes the
discovery; the LLM narrates it.

Per ``model.md`` §2.2:
    E[Δy] = (1 - ρ) · Δy_if_complete
    ŷ(L_s, H) = y_s · (1 + γ_s)^H · (1 + δ_s)^H

The v0_5_0 logic.py uses a hard-coded 25% post-training income lift and
ignores rho/delta. Here we thread both through so the sliders actually move
the math.
"""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass, field
from typing import Any

from pathwise.seasons.build_independence.revisions.v0_5_0.logic import (
    DEFAULT_CAR_OVERHEAD_MONTHLY,
    DEFAULT_RENT_LOW_MONTHLY,
    DEFAULT_TRAINING_TIME_PER_WEEK,
    LifeStateV5,
    PathResult,
    StageResult,
    _check_desirable_extras,
    _check_viable,
    _momentum,
    _recoverability,
)


# ---------------------------------------------------------------------------
# Override schema
# ---------------------------------------------------------------------------


@dataclass
class StageOverride:
    """Per-stage levers the user can drag in the UI."""

    duration_months: float | None = None


@dataclass
class PathOverride:
    """Per-path levers."""

    enabled: bool = True
    # Completion risk for whatever K this path encodes. 0 → guaranteed
    # completion, 1 → guaranteed not. Threads into the post-training income
    # uplift via E[Δy] = (1 - ρ) · base_uplift.
    rho: float | None = None
    # Technology trajectory for the same K. Compounded over the path
    # horizon: ŷ = y · (1 + γ)^H · (1 + δ)^H. -1..+1, signed.
    delta: float | None = None
    # Per-stage overrides keyed by stage id
    stages: dict[str, StageOverride] = field(default_factory=dict)


@dataclass
class GlobalOverride:
    """Knobs that affect every path."""

    rent_monthly: float | None = None
    car_overhead_monthly: float | None = None
    training_hours_per_week: float | None = None
    # Base post-training income multiplier. 1.25 = +25% (the original
    # hard-coded value in v0_5_0/logic.py).
    income_uplift_factor: float | None = None
    # Person-specific recoverability floor R_min. Per §2.5, a path
    # requires R(s_j) >= R_min for every large decision; here we surface
    # it as a slider so users can see how many paths survive a stricter
    # floor.
    r_min: float = 0.4


@dataclass
class MonteCarloSpec:
    """Which inputs vary, and how. Empty → deterministic."""

    samples: int = 0
    # Uniform half-width on rho per path (e.g. 0.15 means rho ± 0.15)
    rho_jitter: float = 0.0
    # Uniform half-width on delta per path
    delta_jitter: float = 0.0
    # Uniform half-width on rent (fraction; 0.2 = ±20%)
    rent_jitter: float = 0.0
    # Uniform half-width on car overhead (fraction)
    car_jitter: float = 0.0
    seed: int | None = None


@dataclass
class SandboxConfig:
    """The full configuration the UI ships to /simulate on every drag."""

    paths: dict[str, PathOverride] = field(default_factory=dict)
    globals: GlobalOverride = field(default_factory=GlobalOverride)
    monte_carlo: MonteCarloSpec = field(default_factory=MonteCarloSpec)


# ---------------------------------------------------------------------------
# Override-aware path scoring (parallels v0_5_0/logic.py, parameterized)
# ---------------------------------------------------------------------------


def _apply_stage_modifiers_override(
    base: LifeStateV5,
    stage: dict[str, Any],
    *,
    rent: float,
    car_overhead: float,
    training_hours_per_week: float,
    rho: float,
    delta: float,
    income_uplift_factor: float,
) -> LifeStateV5:
    """Parameterized version of v0_5_0._apply_stage_modifiers.

    Differences from the baseline:

    * Rent, car overhead, training time/week, and income uplift come from
      the override layer instead of being module constants.
    * ``rho`` discounts the post-training income uplift per §2.2:
      ``E[Δy] = (1 - ρ) · Δy_if_complete``.
    * ``delta`` compounds over the stage duration as a monthly drag on income
      per §2.2: ``ŷ = y · (1 + δ)^(months/12)``. Negative δ → headwind,
      positive → tailwind.
    """
    p = base.p
    c = base.c
    sigma = base.sigma
    y = base.y
    i1 = base.i1
    i3 = base.i3
    eta = base.eta

    duration = float(stage.get("duration_months", 0))

    if stage.get("training_active"):
        p = max(0.0, p - training_hours_per_week)
        if duration > 0:
            sigma -= base.mu * (duration / max(base.tau, duration))

    if stage.get("moves_out"):
        c -= rent
        i3 = max(i3, 4.0)

    if stage.get("car"):
        c -= car_overhead
        i1 = max(i1, 4.0)

    if stage.get("income_growth"):
        # E[Δy] = (1 - ρ) · base_uplift. Base lift is income_uplift_factor;
        # if ρ = 0 → full lift, if ρ = 1 → none.
        base_uplift = max(0.0, income_uplift_factor - 1.0)
        expected_uplift = (1.0 - max(0.0, min(1.0, rho))) * base_uplift
        y = y * (1.0 + expected_uplift)
        c = y - max(base.y - base.c, 0.0)

    # delta compounds across the stage's duration. Months → years.
    if delta and duration > 0:
        y = y * pow(1.0 + delta, duration / 12.0)
        c = y - max(base.y - base.c, 0.0)

    sigma_after = max(0.0, sigma + c * duration)
    r_after = sigma_after / max(base.y - c + 1.0, 1.0)

    if stage.get("training_active") and not stage.get("income_growth"):
        eta = max(eta - 0.3, -2.0)
    if stage.get("income_growth"):
        eta = min(eta + 0.3, 2.0)

    return LifeStateV5(
        **{
            **base.__dict__,
            "p": p,
            "c": c,
            "sigma": sigma_after,
            "r": r_after,
            "y": y,
            "i1": i1,
            "i3": i3,
            "eta": eta,
        }
    )


def _resolve_stage(
    stage: dict[str, Any], override: StageOverride | None
) -> dict[str, Any]:
    if not override:
        return stage
    out = dict(stage)
    if override.duration_months is not None:
        out["duration_months"] = float(override.duration_months)
    return out


def score_path_with_overrides(
    path: dict[str, Any],
    base: LifeStateV5,
    weights: dict[str, float],
    rec_weights: dict[str, float],
    *,
    path_override: PathOverride,
    globals_: GlobalOverride,
) -> PathResult:
    """Drop-in replacement for v0_5_0.score_path that respects overrides."""
    rent = globals_.rent_monthly if globals_.rent_monthly is not None else DEFAULT_RENT_LOW_MONTHLY
    car = (
        globals_.car_overhead_monthly
        if globals_.car_overhead_monthly is not None
        else DEFAULT_CAR_OVERHEAD_MONTHLY
    )
    training_hours = (
        globals_.training_hours_per_week
        if globals_.training_hours_per_week is not None
        else DEFAULT_TRAINING_TIME_PER_WEEK
    )
    income_uplift = (
        globals_.income_uplift_factor
        if globals_.income_uplift_factor is not None
        else 1.25
    )
    rho = path_override.rho if path_override.rho is not None else base.rho
    delta = path_override.delta if path_override.delta is not None else base.delta

    L = base
    stage_results: list[StageResult] = []
    path_momentum = 0.0
    all_viable = True
    min_R = 1.0

    for raw_stage in path["stages"]:
        stage = _resolve_stage(raw_stage, path_override.stages.get(raw_stage["id"]))
        L = _apply_stage_modifiers_override(
            L,
            stage,
            rent=rent,
            car_overhead=car,
            training_hours_per_week=training_hours,
            rho=rho,
            delta=delta,
            income_uplift_factor=income_uplift,
        )
        viable_fails = _check_viable(L)
        viable = not viable_fails
        if not viable:
            all_viable = False
        desirable_fails = viable_fails + _check_desirable_extras(L)
        desirable = not desirable_fails
        m = _momentum(L, weights)
        d_j = float(stage.get("duration_months", 0))
        path_momentum += d_j * m
        rec_inputs = stage.get("recoverability", {}) or {}
        R = _recoverability(rec_inputs, rec_weights)
        min_R = min(min_R, R)
        stage_results.append(
            StageResult(
                id=stage["id"],
                label=stage["label"],
                duration_months=d_j,
                life_state=L,
                viable=viable,
                desirable=desirable,
                fails=desirable_fails,
                momentum=m,
                recoverability=R,
                decision_inputs=rec_inputs,
            )
        )

    terminal = stage_results[-1].desirable if stage_results else False
    return PathResult(
        id=path["id"],
        label=path["label"],
        description=path.get("description", ""),
        bucket=path.get("bucket", "skill_leverage"),
        stages=stage_results,
        path_momentum=path_momentum,
        viable=all_viable,
        terminal_desirable=terminal,
        min_recoverability=min_R,
    )


# ---------------------------------------------------------------------------
# Pareto frontier
# ---------------------------------------------------------------------------


def pareto_frontier(results: list[PathResult]) -> list[str]:
    """Return the IDs of paths on the Pareto frontier of
    ``{path_momentum, min_recoverability}`` — both maximized.

    A path is non-dominated when no other path is ≥ on both axes and > on
    at least one. Only viable paths are eligible — a non-viable path can't
    dominate anything because it isn't actually available.
    """
    eligible = [r for r in results if r.viable]
    frontier_ids: list[str] = []
    for a in eligible:
        dominated = False
        for b in eligible:
            if a is b:
                continue
            if (
                b.path_momentum >= a.path_momentum
                and b.min_recoverability >= a.min_recoverability
                and (
                    b.path_momentum > a.path_momentum
                    or b.min_recoverability > a.min_recoverability
                )
            ):
                dominated = True
                break
        if not dominated:
            frontier_ids.append(a.id)
    return frontier_ids


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------


@dataclass
class MonteCarloStats:
    """Per-path roll-up across MC samples."""

    momentum_p10: float
    momentum_p50: float
    momentum_p90: float
    min_r_p10: float
    min_r_p50: float
    min_r_p90: float
    viable_prob: float
    terminal_desirable_prob: float
    samples: int


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    k = (len(ys) - 1) * p
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    if f == c:
        return ys[f]
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def _jitter(rng: random.Random, base: float, half: float) -> float:
    if half <= 0:
        return base
    return base + (rng.random() * 2 - 1) * half


def _jitter_frac(rng: random.Random, base: float, half_frac: float) -> float:
    if half_frac <= 0:
        return base
    return base * (1 + (rng.random() * 2 - 1) * half_frac)


def run_monte_carlo(
    *,
    paths_raw: list[dict[str, Any]],
    base: LifeStateV5,
    weights: dict[str, float],
    rec_weights: dict[str, float],
    config: SandboxConfig,
) -> dict[str, MonteCarloStats]:
    """Run ``config.monte_carlo.samples`` perturbed simulations.

    For each sample we jitter rho per path, delta per path, and rent/car
    cost globally (fractional jitter). Per-path duration overrides are NOT
    jittered — those are user-set facts, not uncertain estimates.
    """
    mc = config.monte_carlo
    if mc.samples <= 0:
        return {}

    rng = random.Random(mc.seed)

    series: dict[str, dict[str, list[float]]] = {
        p["id"]: {"momentum": [], "min_r": [], "viable": [], "terminal": []}
        for p in paths_raw
    }

    base_globals = config.globals
    base_rent = (
        base_globals.rent_monthly
        if base_globals.rent_monthly is not None
        else DEFAULT_RENT_LOW_MONTHLY
    )
    base_car = (
        base_globals.car_overhead_monthly
        if base_globals.car_overhead_monthly is not None
        else DEFAULT_CAR_OVERHEAD_MONTHLY
    )

    for _ in range(mc.samples):
        sample_globals = GlobalOverride(
            rent_monthly=max(0.0, _jitter_frac(rng, base_rent, mc.rent_jitter)),
            car_overhead_monthly=max(0.0, _jitter_frac(rng, base_car, mc.car_jitter)),
            training_hours_per_week=base_globals.training_hours_per_week,
            income_uplift_factor=base_globals.income_uplift_factor,
            r_min=base_globals.r_min,
        )

        for raw_path in paths_raw:
            base_path_override = config.paths.get(raw_path["id"]) or PathOverride()
            if not base_path_override.enabled:
                continue
            sample_path = PathOverride(
                enabled=True,
                rho=max(
                    0.0,
                    min(
                        1.0,
                        _jitter(
                            rng,
                            base_path_override.rho if base_path_override.rho is not None else base.rho,
                            mc.rho_jitter,
                        ),
                    ),
                ),
                delta=max(
                    -1.0,
                    min(
                        1.0,
                        _jitter(
                            rng,
                            base_path_override.delta if base_path_override.delta is not None else base.delta,
                            mc.delta_jitter,
                        ),
                    ),
                ),
                stages=base_path_override.stages,
            )
            r = score_path_with_overrides(
                raw_path,
                base,
                weights,
                rec_weights,
                path_override=sample_path,
                globals_=sample_globals,
            )
            s = series[raw_path["id"]]
            s["momentum"].append(r.path_momentum)
            s["min_r"].append(r.min_recoverability)
            s["viable"].append(1.0 if r.viable else 0.0)
            s["terminal"].append(1.0 if r.terminal_desirable else 0.0)

    stats: dict[str, MonteCarloStats] = {}
    for pid, s in series.items():
        if not s["momentum"]:
            continue
        stats[pid] = MonteCarloStats(
            momentum_p10=_percentile(s["momentum"], 0.10),
            momentum_p50=_percentile(s["momentum"], 0.50),
            momentum_p90=_percentile(s["momentum"], 0.90),
            min_r_p10=_percentile(s["min_r"], 0.10),
            min_r_p50=_percentile(s["min_r"], 0.50),
            min_r_p90=_percentile(s["min_r"], 0.90),
            viable_prob=sum(s["viable"]) / len(s["viable"]),
            terminal_desirable_prob=sum(s["terminal"]) / len(s["terminal"]),
            samples=len(s["momentum"]),
        )
    return stats


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


@dataclass
class StageView:
    """JSON-friendly per-stage record. Mirrors the fields the UI consumes —
    each stage carries its own viability flag, the most decision-relevant L
    numbers (cash flow, risk buffer, productive hours), the recoverability
    score the recoverability dial controls, and the failure reasons that
    paint a stage red."""

    id: str
    label: str
    duration_months: float
    viable: bool
    desirable: bool
    fails: list[str]
    momentum: float
    recoverability: float
    cash_flow_monthly: float
    risk_buffer_months: float
    productive_hours: float
    decision_inputs: dict[str, float]


@dataclass
class PathView:
    id: str
    label: str
    description: str
    bucket: str
    enabled: bool
    rho_used: float
    delta_used: float
    viable: bool
    terminal_desirable: bool
    on_pareto_frontier: bool
    r_min_satisfied: bool
    path_momentum: float
    min_recoverability: float
    stages: list[StageView]
    monte_carlo: MonteCarloStats | None = None


@dataclass
class SandboxResult:
    paths: list[PathView]
    pareto_frontier: list[str]
    config_echo: dict[str, Any]
    horizon_months: int
    r_min: float


def _stage_view(s: StageResult) -> StageView:
    return StageView(
        id=s.id,
        label=s.label,
        duration_months=s.duration_months,
        viable=s.viable,
        desirable=s.desirable,
        fails=list(s.fails),
        momentum=round(s.momentum, 2),
        recoverability=round(s.recoverability, 3),
        cash_flow_monthly=round(s.life_state.c, 0),
        risk_buffer_months=round(s.life_state.r, 2),
        productive_hours=round(s.life_state.p, 1),
        decision_inputs={k: float(v) for k, v in (s.decision_inputs or {}).items()},
    )


def simulate(
    *,
    paths_raw: list[dict[str, Any]],
    base: LifeStateV5,
    weights: dict[str, float],
    rec_weights: dict[str, float],
    horizon_months: int,
    config: SandboxConfig,
) -> SandboxResult:
    """Run the full sandbox simulation: deterministic + Monte Carlo + Pareto.

    Disabled paths still appear in the result so the UI can show them as
    greyed-out, but they're excluded from the Pareto frontier.
    """
    enabled_results: list[PathResult] = []
    all_views: list[PathView] = []

    for raw_path in paths_raw:
        path_override = config.paths.get(raw_path["id"]) or PathOverride()
        result = score_path_with_overrides(
            raw_path,
            base,
            weights,
            rec_weights,
            path_override=path_override,
            globals_=config.globals,
        )
        if path_override.enabled:
            enabled_results.append(result)
        all_views.append(
            PathView(
                id=result.id,
                label=result.label,
                description=result.description,
                bucket=result.bucket,
                enabled=path_override.enabled,
                rho_used=path_override.rho if path_override.rho is not None else base.rho,
                delta_used=path_override.delta if path_override.delta is not None else base.delta,
                viable=result.viable,
                terminal_desirable=result.terminal_desirable,
                on_pareto_frontier=False,
                r_min_satisfied=result.min_recoverability >= config.globals.r_min,
                path_momentum=round(result.path_momentum, 1),
                min_recoverability=round(result.min_recoverability, 3),
                stages=[_stage_view(s) for s in result.stages],
            )
        )

    frontier = set(pareto_frontier(enabled_results))
    for v in all_views:
        v.on_pareto_frontier = v.id in frontier

    if config.monte_carlo.samples > 0:
        mc_stats = run_monte_carlo(
            paths_raw=paths_raw,
            base=base,
            weights=weights,
            rec_weights=rec_weights,
            config=config,
        )
        for v in all_views:
            v.monte_carlo = mc_stats.get(v.id)

    config_echo = {
        "paths": {
            pid: {
                "enabled": po.enabled,
                "rho": po.rho,
                "delta": po.delta,
                "stages": {sid: asdict(so) for sid, so in po.stages.items()},
            }
            for pid, po in config.paths.items()
        },
        "globals": asdict(config.globals),
        "monte_carlo": asdict(config.monte_carlo),
    }

    return SandboxResult(
        paths=all_views,
        pareto_frontier=sorted(frontier),
        config_echo=config_echo,
        horizon_months=horizon_months,
        r_min=config.globals.r_min,
    )


# ---------------------------------------------------------------------------
# Config parsing (HTTP body → SandboxConfig)
# ---------------------------------------------------------------------------


def parse_config(payload: dict[str, Any]) -> SandboxConfig:
    """Forgiving parse: unknown fields are ignored, missing fields take
    their dataclass defaults. The HTTP layer hands us whatever the UI
    serialized; we don't want a single typo to 500."""
    paths_in = (payload or {}).get("paths") or {}
    paths: dict[str, PathOverride] = {}
    for pid, raw in paths_in.items():
        if not isinstance(raw, dict):
            continue
        stages_in = raw.get("stages") or {}
        stages: dict[str, StageOverride] = {}
        for sid, sraw in stages_in.items():
            if isinstance(sraw, dict):
                stages[sid] = StageOverride(
                    duration_months=_optional_float(sraw.get("duration_months"))
                )
        paths[pid] = PathOverride(
            enabled=bool(raw.get("enabled", True)),
            rho=_optional_float(raw.get("rho")),
            delta=_optional_float(raw.get("delta")),
            stages=stages,
        )

    g_in = (payload or {}).get("globals") or {}
    globals_ = GlobalOverride(
        rent_monthly=_optional_float(g_in.get("rent_monthly")),
        car_overhead_monthly=_optional_float(g_in.get("car_overhead_monthly")),
        training_hours_per_week=_optional_float(g_in.get("training_hours_per_week")),
        income_uplift_factor=_optional_float(g_in.get("income_uplift_factor")),
        r_min=float(g_in.get("r_min", 0.4)),
    )

    mc_in = (payload or {}).get("monte_carlo") or {}
    mc = MonteCarloSpec(
        samples=int(mc_in.get("samples", 0) or 0),
        rho_jitter=float(mc_in.get("rho_jitter", 0.0) or 0.0),
        delta_jitter=float(mc_in.get("delta_jitter", 0.0) or 0.0),
        rent_jitter=float(mc_in.get("rent_jitter", 0.0) or 0.0),
        car_jitter=float(mc_in.get("car_jitter", 0.0) or 0.0),
        seed=mc_in.get("seed") if isinstance(mc_in.get("seed"), int) else None,
    )

    return SandboxConfig(paths=paths, globals=globals_, monte_carlo=mc)


def _optional_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Baseline initial config
# ---------------------------------------------------------------------------


def initial_config(paths_raw: list[dict[str, Any]], base: LifeStateV5) -> SandboxConfig:
    """The opening hand the UI displays before the user has moved anything.

    Mirrors the season pack's defaults — every path enabled, durations from
    yaml, rho/delta from the user's answers, costs from module constants."""
    return SandboxConfig(
        paths={
            p["id"]: PathOverride(
                enabled=True, rho=base.rho, delta=base.delta, stages={}
            )
            for p in paths_raw
        },
        globals=GlobalOverride(
            rent_monthly=DEFAULT_RENT_LOW_MONTHLY,
            car_overhead_monthly=DEFAULT_CAR_OVERHEAD_MONTHLY,
            training_hours_per_week=DEFAULT_TRAINING_TIME_PER_WEEK,
            income_uplift_factor=1.25,
            r_min=0.4,
        ),
        monte_carlo=MonteCarloSpec(),
    )


def result_to_json(result: SandboxResult) -> dict[str, Any]:
    return {
        "paths": [_path_view_to_json(v) for v in result.paths],
        "pareto_frontier": result.pareto_frontier,
        "config_echo": result.config_echo,
        "horizon_months": result.horizon_months,
        "r_min": result.r_min,
    }


def _path_view_to_json(v: PathView) -> dict[str, Any]:
    out = asdict(v)
    if v.monte_carlo is not None:
        out["monte_carlo"] = asdict(v.monte_carlo)
    return out
