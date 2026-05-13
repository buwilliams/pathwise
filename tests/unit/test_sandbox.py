from __future__ import annotations

from typing import Any

import pytest
import yaml

from pathwise.core.sandbox import (
    GlobalOverride,
    MonteCarloSpec,
    PathOverride,
    SandboxConfig,
    StageOverride,
    initial_config,
    parse_config,
    pareto_frontier,
    result_to_json,
    score_path_with_overrides,
    simulate,
)
from pathwise.core.season import get_pack


def _emma_answers_v5() -> dict[str, Any]:
    """A representative completed v0.5.0 questionnaire."""
    return {
        "current_monthly_take_home": 1800,
        "current_monthly_bills": 250,
        "current_savings": 10000,
        "current_debt": 0,
        "emergency_fund_floor": 3000,
        "productive_hours_per_week": 18,
        "buffer_hours_per_week": 8,
        "quality_of_time_now": 4,
        "monthly_pressure_comfort": "mild",
        "lives_with_parents": True,
        "has_car": False,
        "wants_mobility": [],
        "interested_in_training": True,
        "education_modality": "certificate",
        "completion_confidence": 4,
        "max_training_months": 12,
        "training_budget": 2500,
        "desired_two_year_income": 3500,
        "emotional_state_now": "positive",
        "stability_now": 4,
        "physical_health_self": 4,
        "mental_health_self": 4,
        "fitness_practice_freq": "weekly",
        "relational_quality_now": "strong",
    }


def _setup_v5() -> tuple[Any, list[dict[str, Any]], dict[str, float], int]:
    pack = get_pack("build-independence", revision="0.5.0")
    life = pack.logic.compute_life_state(_emma_answers_v5())
    raw = yaml.safe_load((pack.pack_dir / "scenarios.yaml").read_text())
    paths_raw = raw["paths"]
    horizon = int(raw.get("horizon_months", 60))
    rec_weights = yaml.safe_load(
        (pack.pack_dir / "weights.yaml").read_text()
    ).get("recoverability_weights", {})
    return life, paths_raw, pack.weights, rec_weights, horizon, pack


def test_simulate_matches_v0_5_0_baseline_when_no_overrides() -> None:
    """The override-aware simulator with empty overrides should reproduce the
    same path momentum as v0_5_0.score_path within rounding."""
    life, paths_raw, weights, rec_weights, horizon, pack = _setup_v5()
    config = initial_config(paths_raw, life)
    # Wipe out rho/delta in path overrides so we hit the same code path as
    # v0_5_0 (which doesn't apply them).
    for po in config.paths.values():
        po.rho = 0.0
        po.delta = 0.0
    # Match v0_5_0's hard-coded uplift of 25% and the legacy *constant* rent.
    config.globals.income_uplift_factor = 1.25
    result = simulate(
        paths_raw=paths_raw,
        base=life,
        weights=weights,
        rec_weights=rec_weights,
        horizon_months=horizon,
        config=config,
    )
    legacy = pack.logic.score(life, {})
    legacy_by_id = {r.id: r for r in legacy}
    for view in result.paths:
        legacy_row = legacy_by_id.get(view.id)
        assert legacy_row is not None
        assert view.path_momentum == pytest.approx(round(legacy_row.path_momentum, 1), abs=0.5)
        assert view.viable == legacy_row.viable
        assert view.terminal_desirable == legacy_row.terminal_desirable


def test_raising_rho_drags_down_paths_with_income_growth() -> None:
    """ρ → 1 cancels the post-training income lift, so any path that depends
    on an income_growth stage to clear the desirability filter should lose
    terminal-desirable status."""
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config_low = initial_config(paths_raw, life)
    for po in config_low.paths.values():
        po.rho = 0.0  # guaranteed completion
        po.delta = 0.0
    result_low = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config_low,
    )

    config_high = initial_config(paths_raw, life)
    for po in config_high.paths.values():
        po.rho = 1.0  # no income lift at all
        po.delta = 0.0
    result_high = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config_high,
    )

    # Find a path with an income_growth stage and check its terminal income
    # / momentum dropped.
    growth_path_id = None
    for p in paths_raw:
        if any(s.get("income_growth") for s in p["stages"]):
            growth_path_id = p["id"]
            break
    assert growth_path_id is not None

    lo = next(p for p in result_low.paths if p.id == growth_path_id)
    hi = next(p for p in result_high.paths if p.id == growth_path_id)
    # With rho=1, the income lift vanishes → smaller momentum on this path.
    assert lo.path_momentum > hi.path_momentum


def test_negative_delta_compounds_against_path_income() -> None:
    """δ < 0 is a tech headwind. Over a long horizon it should pull income
    down enough that paths in declining fields lose terminal desirability
    or path momentum versus a neutral δ."""
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    neutral = initial_config(paths_raw, life)
    for po in neutral.paths.values():
        po.delta = 0.0
        po.rho = 0.0
    headwind = initial_config(paths_raw, life)
    for po in headwind.paths.values():
        po.delta = -0.10  # -10% annual
        po.rho = 0.0

    n = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=neutral,
    )
    h = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=headwind,
    )
    # Across at least one income_growth path, headwind should drop momentum.
    growth_paths = [
        p["id"] for p in paths_raw
        if any(s.get("income_growth") for s in p["stages"])
    ]
    assert any(
        next(x for x in h.paths if x.id == pid).path_momentum
        < next(x for x in n.paths if x.id == pid).path_momentum
        for pid in growth_paths
    )


def test_dragging_stage_duration_changes_path_momentum() -> None:
    """Moving a stage's duration changes its duration-weighted momentum
    contribution. A 6-month stage shouldn't yield the same path momentum
    as a 60-month one."""
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config = initial_config(paths_raw, life)
    target_path = paths_raw[0]
    target_stage = target_path["stages"][-1]
    long_dur = StageOverride(duration_months=48)
    short_dur = StageOverride(duration_months=6)

    config.paths[target_path["id"]].stages = {target_stage["id"]: long_dur}
    long_result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    config.paths[target_path["id"]].stages = {target_stage["id"]: short_dur}
    short_result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    long_view = next(p for p in long_result.paths if p.id == target_path["id"])
    short_view = next(p for p in short_result.paths if p.id == target_path["id"])
    assert long_view.path_momentum != short_view.path_momentum


def test_rent_lever_flips_viability_in_move_out_paths() -> None:
    """Raising rent through the global lever should push any move-out path
    into negative cash flow and fail the viable filter."""
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    cheap = initial_config(paths_raw, life)
    cheap.globals.rent_monthly = 200
    expensive = initial_config(paths_raw, life)
    expensive.globals.rent_monthly = 4000

    cheap_result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=cheap,
    )
    expensive_result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=expensive,
    )

    move_out_paths = [
        p["id"] for p in paths_raw
        if any(s.get("moves_out") for s in p["stages"])
    ]
    assert move_out_paths, "fixture should include at least one move-out path"
    # At least one move-out path that was viable at cheap rent should fail
    # viability at $4000/mo rent.
    flipped = False
    for pid in move_out_paths:
        cv = next(p for p in cheap_result.paths if p.id == pid)
        ev = next(p for p in expensive_result.paths if p.id == pid)
        if cv.viable and not ev.viable:
            flipped = True
            break
    assert flipped, "expensive rent should make at least one move-out path non-viable"


def test_pareto_frontier_only_contains_viable_paths() -> None:
    """Non-viable paths can't dominate anyone — they're filtered out before
    momentum comparison even happens, per §2.5."""
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config = initial_config(paths_raw, life)
    config.globals.rent_monthly = 5000  # force most move-out paths non-viable
    result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    for pid in result.pareto_frontier:
        view = next(p for p in result.paths if p.id == pid)
        assert view.viable


def test_pareto_frontier_excludes_dominated_paths() -> None:
    """A path beaten on both axes by another enabled, viable path is not
    on the frontier."""
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config = initial_config(paths_raw, life)
    result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    enabled_viable = [p for p in result.paths if p.enabled and p.viable]
    for view in enabled_viable:
        if view.on_pareto_frontier:
            continue
        # Some other enabled+viable path must dominate it.
        dominated_by = [
            o for o in enabled_viable
            if o.id != view.id
            and o.path_momentum >= view.path_momentum
            and o.min_recoverability >= view.min_recoverability
            and (
                o.path_momentum > view.path_momentum
                or o.min_recoverability > view.min_recoverability
            )
        ]
        assert dominated_by, f"{view.id} not on frontier but nothing dominates it"


def test_disabled_path_does_not_count_toward_frontier() -> None:
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config = initial_config(paths_raw, life)
    # Run once to find the current frontier
    base_result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    if not base_result.pareto_frontier:
        pytest.skip("baseline has no viable frontier in this fixture")
    # Disable a path that's on the frontier; its slot may free up for others.
    disabled_id = base_result.pareto_frontier[0]
    config.paths[disabled_id].enabled = False
    after = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    disabled_view = next(p for p in after.paths if p.id == disabled_id)
    assert disabled_view.on_pareto_frontier is False
    assert disabled_id not in after.pareto_frontier


def test_monte_carlo_returns_percentile_band_per_path() -> None:
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config = initial_config(paths_raw, life)
    config.monte_carlo = MonteCarloSpec(
        samples=64,
        rho_jitter=0.2,
        delta_jitter=0.05,
        rent_jitter=0.2,
        car_jitter=0.1,
        seed=42,
    )
    result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    enabled = [p for p in result.paths if p.enabled]
    assert enabled
    for view in enabled:
        assert view.monte_carlo is not None
        mc = view.monte_carlo
        assert mc.samples == 64
        assert mc.momentum_p10 <= mc.momentum_p50 <= mc.momentum_p90
        assert 0.0 <= mc.viable_prob <= 1.0
        assert 0.0 <= mc.terminal_desirable_prob <= 1.0


def test_monte_carlo_seed_is_reproducible() -> None:
    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config = initial_config(paths_raw, life)
    config.monte_carlo = MonteCarloSpec(
        samples=24, rho_jitter=0.15, delta_jitter=0.05,
        rent_jitter=0.2, car_jitter=0.1, seed=7,
    )
    a = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    b = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    a_mc = {p.id: p.monte_carlo for p in a.paths if p.monte_carlo}
    b_mc = {p.id: p.monte_carlo for p in b.paths if p.monte_carlo}
    assert a_mc.keys() == b_mc.keys()
    for pid in a_mc:
        assert a_mc[pid].momentum_p50 == pytest.approx(b_mc[pid].momentum_p50)
        assert a_mc[pid].viable_prob == pytest.approx(b_mc[pid].viable_prob)


def test_parse_config_is_forgiving() -> None:
    """Unknown keys and missing fields don't blow up — the UI gets to ship
    arbitrary patches without worrying about strict validation."""
    cfg = parse_config({
        "paths": {
            "stay_save_train_move": {"enabled": True, "rho": "0.2", "delta": "-0.05",
                                     "stages": {"stay_save": {"duration_months": "12"}}},
            "broken_input": "not a dict",  # ignored
        },
        "globals": {"rent_monthly": "750", "totally_unknown_key": True},
        "monte_carlo": {"samples": 10, "seed": "not an int"},
        "extra_garbage": [1, 2, 3],
    })
    assert cfg.paths["stay_save_train_move"].rho == 0.2
    assert cfg.paths["stay_save_train_move"].delta == -0.05
    assert cfg.paths["stay_save_train_move"].stages["stay_save"].duration_months == 12.0
    assert "broken_input" not in cfg.paths
    assert cfg.globals.rent_monthly == 750.0
    assert cfg.monte_carlo.samples == 10
    assert cfg.monte_carlo.seed is None


def test_result_to_json_is_plain_dicts_and_lists() -> None:
    """The /sandbox response must be JSON-serializable end-to-end."""
    import json

    life, paths_raw, weights, rec_weights, horizon, _ = _setup_v5()
    config = initial_config(paths_raw, life)
    config.monte_carlo = MonteCarloSpec(samples=12, seed=0)
    result = simulate(
        paths_raw=paths_raw, base=life, weights=weights,
        rec_weights=rec_weights, horizon_months=horizon, config=config,
    )
    payload = result_to_json(result)
    # If this round-trips, the FastAPI layer can ship it.
    s = json.dumps(payload)
    assert isinstance(s, str)
    assert "paths" in payload and "pareto_frontier" in payload
