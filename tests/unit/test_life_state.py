from __future__ import annotations

from pathwise.core.life_state import compute_life_state


def test_basic_compute() -> None:
    answers = {
        "current_monthly_take_home": 1800,
        "current_monthly_bills": 300,
        "current_savings": 10000,
        "emergency_fund_floor": 3000,
        "productive_hours_per_week": 15,
        "quality_of_time_now": 4,
        "top_value": "independence",
        "move_out_urgency": 4,
        "has_car": False,
        "lives_with_parents": True,
        "monthly_pressure_comfort": "mild",
        "interested_in_training": True,
    }
    L = compute_life_state(answers)
    assert L.cash_flow_monthly == 1500
    assert L.assets == 10000
    assert L.risk_buffer_months > 20  # 10k/300 capped at 24
    assert L.productive_hours_per_week == 15
    assert L.top_value == "independence"
    assert L.has_car is False
    assert L.lives_with_parents is True


def test_no_bills_infinite_buffer_capped() -> None:
    L = compute_life_state(
        {
            "current_monthly_take_home": 0,
            "current_monthly_bills": 0,
            "current_savings": 5000,
        }
    )
    assert L.risk_buffer_months == 24.0  # capped


def test_buffer_status_bands() -> None:
    L = compute_life_state(
        {"current_monthly_take_home": 0, "current_monthly_bills": 1000, "current_savings": 500}
    )
    assert "fragile" in L.buffer_status

    L = compute_life_state(
        {"current_monthly_take_home": 0, "current_monthly_bills": 1000, "current_savings": 6500}
    )
    assert "strong" in L.buffer_status


def test_defaults_when_answer_missing() -> None:
    L = compute_life_state({})
    assert L.cash_flow_monthly == 0
    assert L.assets == 0
    assert L.lives_with_parents is True  # default
    assert L.has_car is False
    assert L.home_emotional_cost == 1.0  # "fine" default when answer missing


def test_home_emotional_cost_scales_across_options() -> None:
    base = {"lives_with_parents": True}
    assert compute_life_state({**base, "home_emotional_cost": "peaceful"}).home_emotional_cost == 0.0
    assert compute_life_state({**base, "home_emotional_cost": "fine"}).home_emotional_cost == 1.0
    assert compute_life_state({**base, "home_emotional_cost": "tense"}).home_emotional_cost == 2.0
    assert compute_life_state({**base, "home_emotional_cost": "hard"}).home_emotional_cost == 3.0


def test_home_emotional_cost_zero_when_lives_independently() -> None:
    """If the user has already moved out, there's no home cost to pay regardless
    of what they answered."""
    L = compute_life_state(
        {"lives_with_parents": False, "home_emotional_cost": "hard"}
    )
    assert L.home_emotional_cost == 0.0


def test_home_emotional_cost_unknown_value_defaults_to_fine() -> None:
    L = compute_life_state(
        {"lives_with_parents": True, "home_emotional_cost": "weird-value"}
    )
    assert L.home_emotional_cost == 1.0
