"""Scenario simulation, viability filtering, and momentum scoring.

Direct implementation of the formulas in
``seasons/transition_to_adulthood/build-independence.md`` §2.

Each candidate scenario from the season pack is "instantiated" by combining
the user's current life-state with a research bundle (real-world numbers
fetched at plan time). Then we apply:

    S_viable     = {s ∈ S : c_s ≥ 0 ∧ r_s ≥ r_min ∧ p_s ≥ p_min}
    Momentum(s)  = Σ w_i · score_i(s)
    s*           = argmax_{s ∈ S_viable} Momentum(s)

The wisdom (final plan synthesis) is done by the LLM — this layer's job
is to filter and rank so the LLM is grounded in actual numbers.

Scoring components (as of v0.3.0):
    i, n, e, g, s, p, c, r, y      — V/T/A/Y/K momentum components from L
    rec                            — per-decision recoverability (rewards
                                     reversible choices; penalizes irreversible
                                     ones, especially when buffer is thin)

Per the essay (§Momentum Score): emotional cost H does NOT appear directly
in the momentum sum. Each scenario has a per-scenario H(s) computed from
the user's stated home_emotional_cost plus the inherent emotional load of
the choice (move-out arrangement, training discipline, car ownership). H(s)
then depresses e (enjoyable), s (stability), and g (goal progress) when
high. The weights on those three carry the emotional load.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pathwise.core.life_state import LifeState
from pathwise.core.season import Scenario


# ---------------------------------------------------------------------------
# Default numbers (used when no research bundle is available)
# ---------------------------------------------------------------------------

DEFAULTS = {
    # Basic reliable used car (think 10-12yr-old Civic/Corolla/Sentra,
    # ~100-130k miles), national midpoint
    "used_car_price_basic": 5500.0,
    "used_car_insurance_monthly_18yo": 225.0,
    "used_car_gas_and_maint_monthly": 175.0,
    # Rent
    "rent_room_in_shared_house": 750.0,
    "rent_one_bedroom": 1400.0,
    # Short certificate / trade program — community-college tier
    "training_total_cost": 2500.0,
    "training_months": 9.0,
    "training_income_uplift_monthly": 1200.0,
}


# ---------------------------------------------------------------------------
# Scoring config
# ---------------------------------------------------------------------------

# Variable thresholds for viability and quality-of-life floors.
MIN_RISK_BUFFER_MONTHS = 1.5
MIN_PRODUCTIVE_HOURS_PER_WEEK = 5.0


@dataclass
class ScoredScenario:
    id: str
    label: str
    description: str
    viable: bool
    fails: list[str]
    momentum: float

    # Projected scenario state (vs current)
    cash_flow_monthly: float
    risk_buffer_months: float
    productive_hours_per_week: float
    income_monthly: float

    # Deltas from current life-state
    cash_flow_delta: float
    buffer_delta_months: float
    time_delta_hours: float
    income_delta: float

    # Per-component scores (transparency for the plan prompt)
    component_scores: dict[str, float]

    # Per-decision metadata surfaced to the plan prompt so it can render
    # path-specific tags (recoverability label, bucket grouping).
    recoverability: str = "medium"  # high | medium | low
    bucket: str = "skill_leverage"  # fast_freedom | compounding_freedom | skill_leverage

    # Pretty-printed deltas (for templates)
    @property
    def cash_flow_delta_str(self) -> str:
        return _signed_money(self.cash_flow_delta)

    @property
    def buffer_delta_str(self) -> str:
        return f"{self.buffer_delta_months:+.1f}mo"

    @property
    def time_delta_str(self) -> str:
        return f"{self.time_delta_hours:+.0f}h/wk"


def _signed_money(v: float) -> str:
    sign = "+" if v >= 0 else "-"
    return f"{sign}${abs(v):,.0f}"


def _research(research: dict[str, Any] | None, *path: str, default: float) -> float:
    if not research:
        return default
    cur: Any = research
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    try:
        return float(cur)
    except (TypeError, ValueError):
        return default


def _car_price(research: dict[str, Any] | None) -> float:
    """Midpoint price of a basic reliable used car in the user's market."""
    low = _research(
        research,
        "used_car",
        "basic_tier",
        "price_low",
        default=DEFAULTS["used_car_price_basic"],
    )
    high = _research(
        research,
        "used_car",
        "basic_tier",
        "price_high",
        default=DEFAULTS["used_car_price_basic"],
    )
    return (low + high) / 2 if (low and high) else (low or high or DEFAULTS["used_car_price_basic"])


def _car_monthly_cost(research: dict[str, Any] | None) -> float:
    """Operating cost only: insurance + gas + maintenance.

    Purchase price is treated as a one-time hit to assets, not amortized into
    monthly cash flow — we want to model the realistic decision: 'I write a
    check, my buffer drops, my monthly burn goes up by operating costs.'
    """
    ins_low = _research(
        research,
        "used_car",
        "insurance_18yo_monthly_low",
        default=DEFAULTS["used_car_insurance_monthly_18yo"],
    )
    ins_high = _research(
        research,
        "used_car",
        "insurance_18yo_monthly_high",
        default=DEFAULTS["used_car_insurance_monthly_18yo"],
    )
    insurance = (ins_low + ins_high) / 2
    return insurance + DEFAULTS["used_car_gas_and_maint_monthly"]


def _car_one_time_cost(research: dict[str, Any] | None) -> float:
    return _car_price(research)


def _move_out_monthly_rent(research: dict[str, Any] | None) -> float:
    return _research(
        research,
        "rent",
        "room_in_shared_house_monthly_low",
        default=DEFAULTS["rent_room_in_shared_house"],
    )


def _training_monthly_cost(research: dict[str, Any] | None) -> float:
    paths = (research or {}).get("skill_paths") or []
    if paths:
        try:
            best = paths[0]
            tuition = float(best.get("tuition_total") or DEFAULTS["training_total_cost"])
            months = float(best.get("months_to_complete") or DEFAULTS["training_months"])
            return tuition / max(1.0, months)
        except (TypeError, ValueError):
            pass
    return DEFAULTS["training_total_cost"] / DEFAULTS["training_months"]


def _training_income_uplift(research: dict[str, Any] | None) -> float:
    paths = (research or {}).get("skill_paths") or []
    if paths:
        try:
            best = paths[0]
            wages_low = float(best.get("entry_wage_monthly_low") or 0)
            wages_high = float(best.get("entry_wage_monthly_high") or 0)
            if wages_low and wages_high:
                return (wages_low + wages_high) / 2
        except (TypeError, ValueError):
            pass
    return DEFAULTS["training_income_uplift_monthly"]


def _instantiate(
    scenario: Scenario, life: LifeState, research: dict[str, Any] | None
) -> dict[str, float]:
    """Project the scenario's monthly cash-flow / buffer / time / income."""
    obligations = life.monthly_obligations
    income = life.current_income_monthly
    productive = life.productive_hours_per_week
    assets = life.assets

    if scenario.car and not life.has_car:
        obligations += _car_monthly_cost(research)
        assets -= _car_one_time_cost(research)

    if scenario.moves_out and life.lives_with_parents:
        obligations += _move_out_monthly_rent(research)

    if scenario.income_growth and life.interested_in_training:
        obligations += _training_monthly_cost(research)
        productive = max(0.0, productive - 8.0)  # ~8h/wk of training time
        # Income uplift assumed to land at end of training horizon — for the
        # 12-month outlook, treat as half-realized so the score reflects the
        # path's promise without overstating it.
        income += _training_income_uplift(research) * 0.5
    elif scenario.income_growth:
        # Working more hours instead of training
        income += income * 0.20

    cash_flow = income - obligations
    risk_buffer_months = (
        (assets / obligations) if obligations > 0 else float("inf")
    )

    return {
        "cash_flow": cash_flow,
        "buffer_months": min(risk_buffer_months, 24.0),
        "productive_hours": productive,
        "income": income,
        "assets_after": assets,
    }


# ---------------------------------------------------------------------------
# Per-variable score functions, each in roughly [-1, +1]
# ---------------------------------------------------------------------------


def _score_cash_flow(state: dict[str, float], life: LifeState) -> float:
    if state["cash_flow"] < 0:
        return -1.0
    if life.current_income_monthly <= 0:
        return 0.0 if state["cash_flow"] == 0 else 1.0
    return min(1.0, state["cash_flow"] / max(1.0, life.current_income_monthly))


def _score_risk_buffer(state: dict[str, float], life: LifeState) -> float:
    target = 6.0  # months
    return max(-1.0, min(1.0, (state["buffer_months"] - target) / target + 0.5))


def _score_income(state: dict[str, float], life: LifeState) -> float:
    base = max(1.0, life.current_income_monthly)
    return max(-1.0, min(1.5, (state["income"] - life.current_income_monthly) / base))


def _score_productive_time(state: dict[str, float], life: LifeState) -> float:
    if state["productive_hours"] < MIN_PRODUCTIVE_HOURS_PER_WEEK:
        return -1.0
    base = max(1.0, life.productive_hours_per_week)
    delta = (state["productive_hours"] - life.productive_hours_per_week) / base
    return max(-1.0, min(1.0, delta))


def _score_independence(scenario: Scenario, life: LifeState) -> float:
    """Composite of i₁..i₄. Mobility (car) and financial dominate the early ladder."""
    score = 0.0
    if scenario.car and not life.has_car:
        score += 0.5  # i₁ mobility
    if scenario.moves_out and life.lives_with_parents:
        score += 0.5  # i₃ residential
    # i₂ financial is reflected via cash_flow + buffer scores
    # i₄ decision is reflected via productive time + income growth
    return min(1.0, score)


def _score_net_worth(state: dict[str, float], life: LifeState) -> float:
    # Project 12-month net worth change as a fraction of current assets
    base = max(1000.0, life.assets)
    delta = state["cash_flow"] * 12 + (state["assets_after"] - life.assets)
    return max(-1.0, min(1.0, delta / base))


def _score_enjoyable(scenario: Scenario, state: dict[str, float], life: LifeState) -> float:
    # Heavy negative cash flow or zero productive time crushes enjoyment
    if state["cash_flow"] < 0:
        return -0.5
    if state["productive_hours"] < MIN_PRODUCTIVE_HOURS_PER_WEEK:
        return -0.5
    # Per essay §Emotional Cost: H depresses enjoyment when high.
    return max(-1.0, 0.0 - _h_penalty(_scenario_H(scenario, life), 0.30))


def _score_goals(scenario: Scenario, life: LifeState) -> float:
    if scenario.income_growth and life.interested_in_training:
        base = 1.0
    elif scenario.income_growth:
        base = 0.3
    else:
        base = 0.0
    # H depresses goal progress when emotional pressure blocks momentum.
    return max(-1.0, base - _h_penalty(_scenario_H(scenario, life), 0.20))


def _scenario_H(scenario: Scenario, life: LifeState) -> float:
    """Per-scenario emotional cost in 0..3, per build-independence.md §Emotional Cost.

    H is the cost paid by *this specific scenario*, not just by the home situation.
    It accumulates across the emotionally-loaded commitments the scenario implies:

    - Stay-home scenarios pay the user's stated stay-home emotional cost
      (peaceful=0, fine=1, tense=2, hard=3 from the questionnaire).
    - Move-out scenarios pay a baseline 1.0 for the financial pressure / new
      arrangement / household labor a fresh living situation introduces.
    - Acquiring a car the teen doesn't have adds maintenance anxiety / repair
      stress (+0.3).
    - Pursuing intensive training when they're open to it adds discipline cost
      and delayed gratification (+0.5).
    """
    if scenario.moves_out or not life.lives_with_parents:
        h = 1.0  # baseline emotional cost of move-out / living independently
    else:
        h = life.home_emotional_cost  # the user's stated cost of staying home

    if scenario.car and not life.has_car:
        h += 0.3
    if scenario.income_growth and life.interested_in_training:
        h += 0.5
    return min(3.0, h)


def _h_penalty(h: float, scale: float) -> float:
    """Linear penalty applied to e/s/g when H is above the 'fine' baseline of 1.0.

    Returns 0 when H ≤ 1.0; grows linearly above. The scale parameter lets
    callers tune how steeply each variable degrades:
        e: 0.30  (enjoyment is most directly hit by emotional cost)
        s: 0.25  (stability gets hit, but not as completely)
        g: 0.20  (goals can sometimes survive emotional pressure)
    """
    return max(0.0, h - 1.0) * scale


def _score_recoverability(scenario: Scenario, life: LifeState) -> float:
    """Reward reversible decisions; penalize irreversible ones, more so when
    the user's buffer is already thin (low recoverability + thin buffer is
    the danger combination the model wants to flag explicitly).
    """
    base = {"high": 0.5, "medium": 0.0, "low": -0.5}.get(scenario.recoverability, 0.0)
    if scenario.recoverability == "low" and life.risk_buffer_months < MIN_RISK_BUFFER_MONTHS:
        base *= 1.5  # thin buffer + irreversible decision = compounded danger
    return max(-1.0, min(1.0, base))


def _score_stability(scenario: Scenario, state: dict[str, float], life: LifeState) -> float:
    if state["cash_flow"] < 0:
        return -1.0
    if life.emergency_fund_floor > 0 and state["assets_after"] < life.emergency_fund_floor:
        return -1.0
    if state["buffer_months"] < MIN_RISK_BUFFER_MONTHS:
        return -0.5
    pressure_ok = {"zero": 1.0, "mild": 0.7, "moderate": 0.4, "high": 0.0}.get(
        life.monthly_pressure_comfort, 0.5
    )
    base = (state["buffer_months"] / 6.0) * pressure_ok
    clamped = max(-1.0, min(1.0, base))
    # H depresses emotional safety when high. Apply *after* the clamp so a
    # maxed-out stability score still shows the H hit.
    return max(-1.0, clamped - _h_penalty(_scenario_H(scenario, life), 0.25))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_scenario(
    scenario: Scenario,
    life: LifeState,
    weights: dict[str, float],
    research: dict[str, Any] | None = None,
) -> ScoredScenario:
    state = _instantiate(scenario, life, research)

    component_scores = {
        "i": _score_independence(scenario, life),
        "n": _score_net_worth(state, life),
        "e": _score_enjoyable(scenario, state, life),
        "g": _score_goals(scenario, life),
        "s": _score_stability(scenario, state, life),
        "p": _score_productive_time(state, life),
        "c": _score_cash_flow(state, life),
        "r": _score_risk_buffer(state, life),
        "y": _score_income(state, life),
        "rec": _score_recoverability(scenario, life),
    }

    momentum = sum(weights.get(k, 0.0) * v for k, v in component_scores.items())

    fails: list[str] = []
    if state["cash_flow"] < 0:
        fails.append("negative cash flow")
    if life.emergency_fund_floor > 0 and state["assets_after"] < life.emergency_fund_floor:
        fails.append(
            f"would drop below your emergency floor of ${life.emergency_fund_floor:,.0f}"
        )
    if state["buffer_months"] < MIN_RISK_BUFFER_MONTHS:
        fails.append(f"buffer below {MIN_RISK_BUFFER_MONTHS:.1f} months")
    if state["productive_hours"] < MIN_PRODUCTIVE_HOURS_PER_WEEK:
        fails.append("too little productive time")

    return ScoredScenario(
        id=scenario.id,
        label=scenario.label,
        description=scenario.description,
        viable=not fails,
        fails=fails,
        momentum=momentum,
        cash_flow_monthly=state["cash_flow"],
        risk_buffer_months=state["buffer_months"],
        productive_hours_per_week=state["productive_hours"],
        income_monthly=state["income"],
        cash_flow_delta=state["cash_flow"] - life.cash_flow_monthly,
        buffer_delta_months=state["buffer_months"] - life.risk_buffer_months,
        time_delta_hours=state["productive_hours"] - life.productive_hours_per_week,
        income_delta=state["income"] - life.current_income_monthly,
        component_scores=component_scores,
        recoverability=scenario.recoverability,
        bucket=scenario.bucket,
    )


def score_all(
    scenarios: list[Scenario],
    life: LifeState,
    weights: dict[str, float],
    research: dict[str, Any] | None = None,
) -> list[ScoredScenario]:
    """Score every scenario, return sorted by momentum desc.

    Note: viable scenarios float to the top among themselves; we keep
    non-viable ones in the list so the LLM can explain why they were rejected.
    """
    scored = [score_scenario(s, life, weights, research) for s in scenarios]
    scored.sort(key=lambda s: (s.viable, s.momentum), reverse=True)
    return scored
