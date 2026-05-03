from __future__ import annotations

from pathwise.core.life_state import compute_life_state
from pathwise.core.momentum import (
    _scenario_H,
    _score_recoverability,
    score_all,
    score_scenario,
)
from pathwise.core.season import Scenario, get_pack


def _emma_answers() -> dict:
    """Roughly Emma's situation: home, no car, $10k saved, modest job."""
    return {
        "current_monthly_take_home": 1800,
        "current_monthly_bills": 250,
        "current_savings": 10000,
        "emergency_fund_floor": 3000,
        "productive_hours_per_week": 18,
        "quality_of_time_now": 4,
        "top_value": "independence",
        "move_out_urgency": 4,
        "move_out_horizon": "1yr",
        "has_car": False,
        "lives_with_parents": True,
        "monthly_pressure_comfort": "mild",
        "interested_in_training": True,
        "training_modality": "certificate",
        "max_training_months": 12,
        "desired_two_year_income": 3500,
    }


def test_status_quo_scenario_viable() -> None:
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    s = next(x for x in pack.scenarios if x.id == "stay_no_car_save")
    scored = score_scenario(s, life, pack.weights)
    assert scored.viable
    assert scored.cash_flow_monthly > 0


def test_move_out_with_car_in_expensive_market_is_unviable() -> None:
    """Per Emma's model: in any market with realistic urban rent, moving out
    while buying a car on $1800/mo income should fail viability."""
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    expensive_market = {
        "rent": {
            "room_in_shared_house_monthly_low": 1300,
            "room_in_shared_house_monthly_high": 1600,
        }
    }
    s = next(x for x in pack.scenarios if x.id == "move_out_with_car")
    scored = score_scenario(s, life, pack.weights, expensive_market)
    assert not scored.viable, f"expected unviable, got fails={scored.fails}"


def test_move_out_with_car_ranks_below_independence_ladder() -> None:
    """The Emma model's central criticism: doing both at once should rank
    below the staged-independence path."""
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    scored = score_all(pack.scenarios, life, pack.weights)
    by_id = {s.id: s for s in scored}
    assert by_id["low_rent_modest_car_grow_income"].momentum > by_id["move_out_with_car"].momentum
    assert by_id["train_for_better_income"].momentum > by_id["move_out_with_car"].momentum


def test_income_growth_paths_beat_pure_status_quo() -> None:
    """Per Emma's model §Skills: K → Y → M → T → V means skill-building is
    a lever that should rank above plain status-quo for someone open to it."""
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    scored = score_all(pack.scenarios, life, pack.weights)
    by_id = {s.id: s for s in scored}
    assert by_id["train_for_better_income"].momentum > by_id["stay_no_car_save"].momentum


def test_all_scenarios_scored_and_sorted() -> None:
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    scored = score_all(pack.scenarios, life, pack.weights)
    assert len(scored) == len(pack.scenarios)
    # Viable scenarios come first
    viability_seq = [s.viable for s in scored]
    assert viability_seq == sorted(viability_seq, reverse=True)
    # Within each viability tier, sorted by momentum desc
    viable_momenta = [s.momentum for s in scored if s.viable]
    assert viable_momenta == sorted(viable_momenta, reverse=True)


def test_research_overrides_defaults() -> None:
    """Higher local rent should make move-out scenarios harder to keep viable."""
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    cheap = {
        "rent": {
            "room_in_shared_house_monthly_low": 400,
            "room_in_shared_house_monthly_high": 500,
        }
    }
    expensive = {
        "rent": {
            "room_in_shared_house_monthly_low": 1200,
            "room_in_shared_house_monthly_high": 1500,
        }
    }
    s = next(x for x in pack.scenarios if x.id == "move_out_no_car")
    cheap_score = score_scenario(s, life, pack.weights, cheap)
    exp_score = score_scenario(s, life, pack.weights, expensive)
    assert cheap_score.cash_flow_monthly > exp_score.cash_flow_monthly


def _make_scenario(
    *, moves_out: bool = False, recoverability: str = "medium"
) -> Scenario:
    return Scenario(
        id="test",
        label="test",
        description="",
        car=False,
        moves_out=moves_out,
        income_growth=False,
        recoverability=recoverability,
    )


def test_scenario_H_stay_home_uses_user_stated_cost() -> None:
    """Per essay §Emotional Cost: stay-home scenarios pay the user's stated H."""
    for choice, expected in [("peaceful", 0.0), ("fine", 1.0), ("tense", 2.0), ("hard", 3.0)]:
        life = compute_life_state(
            {"lives_with_parents": True, "home_emotional_cost": choice}
        )
        assert _scenario_H(_make_scenario(moves_out=False), life) == expected


def test_scenario_H_move_out_baseline_is_one() -> None:
    """Move-out scenarios pay a baseline H regardless of how nice home was —
    financial pressure / new arrangement / household labor."""
    for choice in ["peaceful", "fine", "tense", "hard"]:
        life = compute_life_state(
            {"lives_with_parents": True, "home_emotional_cost": choice}
        )
        assert _scenario_H(_make_scenario(moves_out=True), life) == 1.0


def test_scenario_H_already_independent_pays_baseline() -> None:
    """Someone who already lives independently pays the move-out baseline,
    not the user's home-emotional-cost answer (which would be irrelevant)."""
    life = compute_life_state(
        {"lives_with_parents": False, "home_emotional_cost": "hard"}
    )
    assert _scenario_H(_make_scenario(moves_out=False), life) == 1.0


def test_scenario_H_accumulates_extra_emotional_loads() -> None:
    """Car ownership and intensive training add to H per the essay's examples table."""
    life = compute_life_state(
        {"lives_with_parents": True, "home_emotional_cost": "fine", "interested_in_training": True}
    )
    base = _scenario_H(Scenario(id="x", label="x", description="", car=False, moves_out=False, income_growth=False), life)
    with_car = _scenario_H(Scenario(id="x", label="x", description="", car=True, moves_out=False, income_growth=False), life)
    with_training = _scenario_H(Scenario(id="x", label="x", description="", car=False, moves_out=False, income_growth=True), life)
    with_both = _scenario_H(Scenario(id="x", label="x", description="", car=True, moves_out=False, income_growth=True), life)
    assert with_car == base + 0.3
    assert with_training == base + 0.5
    assert with_both == base + 0.8


def test_high_H_depresses_enjoyable_stability_goals_via_penalty() -> None:
    """Hard home + stay-home scenario should score worse on e/s/g than the
    same scenario with peaceful home, even though i/n/y/r are identical."""
    pack = get_pack("build-independence", revision="0.4.0")
    base_answers = _emma_answers()
    stay = next(x for x in pack.scenarios if x.id == "stay_no_car_save")

    peaceful = compute_life_state({**base_answers, "home_emotional_cost": "peaceful"})
    hard = compute_life_state({**base_answers, "home_emotional_cost": "hard"})

    p_scored = score_scenario(stay, peaceful, pack.weights)
    h_scored = score_scenario(stay, hard, pack.weights)

    # H modulates e, s, g via _h_penalty — each should be lower under hard home.
    assert h_scored.component_scores["e"] < p_scored.component_scores["e"]
    assert h_scored.component_scores["s"] < p_scored.component_scores["s"]
    # Goals: stay_no_car_save has income_growth=False, so the base is 0.0 for
    # both, but H penalty (scale 0.20) still depresses hard relative to peaceful.
    assert h_scored.component_scores["g"] < p_scored.component_scores["g"]
    # Total momentum should reflect the e/s/g hit.
    assert h_scored.momentum < p_scored.momentum


def test_h_does_not_appear_in_component_scores() -> None:
    """Per essay: H does not appear directly in the score. Verify no `h` key."""
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    s = pack.scenarios[0]
    scored = score_scenario(s, life, pack.weights)
    assert "h" not in scored.component_scores


def test_score_recoverability_returns_expected_bands() -> None:
    """Healthy buffer so the low-R penalty isn't compounded."""
    life = compute_life_state(
        {
            "current_monthly_take_home": 2000,
            "current_monthly_bills": 200,
            "current_savings": 5000,  # buffer = 25 months → safe
            "lives_with_parents": True,
        }
    )
    assert _score_recoverability(_make_scenario(recoverability="high"), life) == 0.5
    assert _score_recoverability(_make_scenario(recoverability="medium"), life) == 0.0
    assert _score_recoverability(_make_scenario(recoverability="low"), life) == -0.5


def test_score_recoverability_compounds_when_buffer_thin() -> None:
    """Low-R + thin buffer = the danger combination → extra penalty."""
    life = compute_life_state(
        {
            "current_monthly_take_home": 1000,
            "current_monthly_bills": 800,
            "current_savings": 800,  # buffer = 1.0 month → below MIN of 1.5
            "lives_with_parents": True,
        }
    )
    safe_buffer_low_r = -0.5
    actual = _score_recoverability(_make_scenario(recoverability="low"), life)
    assert actual < safe_buffer_low_r  # -0.5 * 1.5 = -0.75


def test_scored_scenario_carries_recoverability_and_bucket() -> None:
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(_emma_answers())
    s = next(x for x in pack.scenarios if x.id == "move_out_with_car")
    scored = score_scenario(s, life, pack.weights)
    assert scored.recoverability == "low"
    assert scored.bucket == "fast_freedom"


def test_no_income_zero_buffer_is_fragile() -> None:
    pack = get_pack("build-independence", revision="0.4.0")
    life = compute_life_state(
        {
            "current_monthly_take_home": 0,
            "current_monthly_bills": 200,
            "current_savings": 100,
            "emergency_fund_floor": 500,
            "productive_hours_per_week": 20,
            "lives_with_parents": True,
            "interested_in_training": False,
        }
    )
    scored = score_all(pack.scenarios, life, pack.weights)
    # Almost everything should fail viability
    viable = [s for s in scored if s.viable]
    assert len(viable) <= 2
