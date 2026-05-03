"""Pure functions: questionnaire answers → current life-state L.

Direct encoding of the formal model in
``seasons/build_independence/revisions/v0_3_0/model.md`` §1.

L = {V, T, M, Y, K, H}

H (home emotional cost) is sourced from the optional ``home_emotional_cost``
question; staying home is not treated as a costless reference point.

R (recoverability) lives on each scenario, not on the life-state — see
``core/season.py:Scenario`` and ``core/momentum.py``.

We only model the parts the questionnaire actually surfaces; what we don't
have, we leave as None and the LLM is told to be transparent about it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LifeState:
    # Money — M = {c, a, d, r}
    cash_flow_monthly: float
    assets: float
    monthly_obligations: float
    risk_buffer_months: float  # r expressed in months of obligations

    # Income — Y = {y, ...}
    current_income_monthly: float
    desired_two_year_income: float | None

    # Time — T = {p, q}
    productive_hours_per_week: float
    quality_of_time: int  # 1-5

    # Values — V (subset; full ranking comes from top_value + scale answers)
    top_value: str | None
    move_out_urgency: int  # 1-5

    # Profile flags
    has_car: bool
    lives_with_parents: bool

    # User-stated floors / preferences
    emergency_fund_floor: float
    monthly_pressure_comfort: str
    interested_in_training: bool

    # Home emotional cost (H) — 0.0 (peaceful) → 3.0 (hard).
    # Forced to 0.0 when the user doesn't live with family.
    home_emotional_cost: float = 1.0

    # Derived qualitative bands for the plan prompt
    @property
    def buffer_status(self) -> str:
        if self.risk_buffer_months >= 6:
            return "strong (>=6 months)"
        if self.risk_buffer_months >= 3:
            return "ok (3–6 months)"
        if self.risk_buffer_months >= 1:
            return "thin (1–3 months)"
        return "fragile (<1 month)"

    @property
    def productive_time_band(self) -> str:
        p = self.productive_hours_per_week
        if p >= 20:
            return "high (20+ hrs/week)"
        if p >= 10:
            return "moderate (10–20 hrs/week)"
        if p >= 5:
            return "low (5–10 hrs/week)"
        return "very low (<5 hrs/week)"


def _num(answers: dict[str, Any], key: str, default: float = 0.0) -> float:
    v = answers.get(key)
    if v in (None, "", []):
        return default
    return float(v)


def _bool(answers: dict[str, Any], key: str, default: bool = False) -> bool:
    v = answers.get(key)
    if v is None:
        return default
    return bool(v)


def _str(answers: dict[str, Any], key: str, default: str | None = None) -> str | None:
    v = answers.get(key)
    if v in (None, "", []):
        return default
    return str(v)


_HOME_EMOTIONAL_COST_SCALE = {
    "peaceful": 0.0,
    "fine": 1.0,
    "tense": 2.0,
    "hard": 3.0,
}


def _home_emotional_cost(answers: dict[str, Any], lives_with_parents: bool) -> float:
    """Map the optional ``home_emotional_cost`` answer onto a 0..3 scale.

    Forced to 0.0 when the user doesn't live with family — there's no home
    cost to pay if you've already moved out. Defaults to 1.0 (fine) when
    the answer is missing so existing users without this answer don't get
    penalized either way.
    """
    if not lives_with_parents:
        return 0.0
    raw = answers.get("home_emotional_cost")
    if not raw:
        return 1.0
    return _HOME_EMOTIONAL_COST_SCALE.get(str(raw), 1.0)


def compute_life_state(answers: dict[str, Any]) -> LifeState:
    income = _num(answers, "current_monthly_take_home")
    bills = _num(answers, "current_monthly_bills")
    savings = _num(answers, "current_savings")
    floor = _num(answers, "emergency_fund_floor")
    lives_with_parents = _bool(answers, "lives_with_parents", True)

    # Treat current monthly obligations as bills (rent is captured separately
    # only when moving-out scenarios kick in).
    obligations = bills
    cash_flow = income - obligations
    risk_buffer_months = (savings / obligations) if obligations > 0 else float("inf")

    return LifeState(
        cash_flow_monthly=cash_flow,
        assets=savings,
        monthly_obligations=obligations,
        risk_buffer_months=min(risk_buffer_months, 24.0),  # cap displayed value
        current_income_monthly=income,
        desired_two_year_income=(
            _num(answers, "desired_two_year_income")
            if "desired_two_year_income" in answers
            else None
        ),
        productive_hours_per_week=_num(answers, "productive_hours_per_week"),
        quality_of_time=int(_num(answers, "quality_of_time_now", 3)),
        top_value=_str(answers, "top_value"),
        move_out_urgency=int(_num(answers, "move_out_urgency", 3)),
        has_car=_bool(answers, "has_car"),
        lives_with_parents=lives_with_parents,
        emergency_fund_floor=floor,
        monthly_pressure_comfort=_str(answers, "monthly_pressure_comfort", "mild") or "mild",
        interested_in_training=_bool(answers, "interested_in_training"),
        home_emotional_cost=_home_emotional_cost(answers, lives_with_parents),
    )
