from __future__ import annotations

from pathwise.core.life_state import compute_life_state
from pathwise.core.momentum import (
    _score_home_emotional,
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
    pack = get_pack("transition-to-adulthood")
    life = compute_life_state(_emma_answers())
    s = next(x for x in pack.scenarios if x.id == "stay_no_car_save")
    scored = score_scenario(s, life, pack.weights)
    assert scored.viable
    assert scored.cash_flow_monthly > 0


def test_move_out_with_car_in_expensive_market_is_unviable() -> None:
    """Per Emma's model: in any market with realistic urban rent, moving out
    while buying a car on $1800/mo income should fail viability."""
    pack = get_pack("transition-to-adulthood")
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
    pack = get_pack("transition-to-adulthood")
    life = compute_life_state(_emma_answers())
    scored = score_all(pack.scenarios, life, pack.weights)
    by_id = {s.id: s for s in scored}
    assert by_id["low_rent_modest_car_grow_income"].momentum > by_id["move_out_with_car"].momentum
    assert by_id["train_for_better_income"].momentum > by_id["move_out_with_car"].momentum


def test_income_growth_paths_beat_pure_status_quo() -> None:
    """Per Emma's model §Skills: K → Y → M → T → V means skill-building is
    a lever that should rank above plain status-quo for someone open to it."""
    pack = get_pack("transition-to-adulthood")
    life = compute_life_state(_emma_answers())
    scored = score_all(pack.scenarios, life, pack.weights)
    by_id = {s.id: s for s in scored}
    assert by_id["train_for_better_income"].momentum > by_id["stay_no_car_save"].momentum


def test_all_scenarios_scored_and_sorted() -> None:
    pack = get_pack("transition-to-adulthood")
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
    pack = get_pack("transition-to-adulthood")
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


def test_score_home_emotional_rewards_moving_out_when_home_is_hard() -> None:
    life = compute_life_state(
        {"lives_with_parents": True, "home_emotional_cost": "hard"}
    )
    move_out = _make_scenario(moves_out=True)
    score = _score_home_emotional(move_out, life)
    assert score > 0.5  # hard home + move-out scenario = strong positive


def test_score_home_emotional_penalizes_moving_out_when_home_is_peaceful() -> None:
    life = compute_life_state(
        {"lives_with_parents": True, "home_emotional_cost": "peaceful"}
    )
    move_out = _make_scenario(moves_out=True)
    score = _score_home_emotional(move_out, life)
    assert score < 0  # peaceful home + move-out = mild negative


def test_score_home_emotional_penalizes_staying_when_home_is_hard() -> None:
    life = compute_life_state(
        {"lives_with_parents": True, "home_emotional_cost": "hard"}
    )
    stay = _make_scenario(moves_out=False)
    assert _score_home_emotional(stay, life) < -0.5


def test_score_home_emotional_neutral_when_home_is_fine_and_staying() -> None:
    life = compute_life_state(
        {"lives_with_parents": True, "home_emotional_cost": "fine"}
    )
    stay = _make_scenario(moves_out=False)
    assert _score_home_emotional(stay, life) == 0.0


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
    pack = get_pack("transition-to-adulthood")
    life = compute_life_state(_emma_answers())
    s = next(x for x in pack.scenarios if x.id == "move_out_with_car")
    scored = score_scenario(s, life, pack.weights)
    assert scored.recoverability == "low"
    assert scored.bucket == "fast_freedom"


def test_no_income_zero_buffer_is_fragile() -> None:
    pack = get_pack("transition-to-adulthood")
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
