"""Midlife v0_1_0 logic: shares the L = {V, T, A, K, W} math with
build-independence v0_5_0, with midlife-specific derivation of L from
answers and midlife-named path buckets.

* ``derive_life_state`` derives the 21 scored scalar components from the
  user's midlife answers (relationship_status, has_dependents,
  career_feeling, debt_pressure, etc. instead of the teen-only
  has_car / lives_with_parents axes).
* ``score_path`` is reused unchanged from the v0_5_0 logic — the
  scoring math is the same model.
* ``build_plan_context`` declares midlife-specific bucket keys
  (``bold_change``, ``compounding_change``, ``creative_reinvention``)
  so the plan template can render them as named sections.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pathwise.seasons._base import BaseLogic


# ---------------------------------------------------------------------------
# Life-state — same shape as build-independence v0_5_0
# ---------------------------------------------------------------------------


@dataclass
class LifeStateV1:
    # Values (V)
    i1: float                    # mobility / location agency (0..5)
    i2: float                    # financial independence (0..5)
    i3: float                    # residential / domestic alignment (0..5)
    i4: float                    # decision independence (0..5)
    e: float                     # enjoyable life experience (0..5)
    g: float                     # goal progress (1..5)
    beta: float                  # stability / emotional safety (1..5)

    # Time (T)
    p: float                     # productive hours per week
    b: float                     # buffer hours per week
    q: float                     # quality of time / energy (1..5)

    # Assets (A)
    c: float                     # monthly cash flow ($)
    sigma: float                 # savings ($) — liquid + retirement
    d: float                     # debt ($)
    r: float                     # risk buffer (months of overhead the liquid savings cover)
    y: float                     # income monthly ($, household)
    gamma: float                 # income growth rate (annual fraction)

    # Capability (K) — tracked but not directly scored
    k: str                       # path label (free-form)
    tau: float                   # training months
    mu: float                    # training money budget ($)
    rho: float                   # completion risk (0..1, low=likely to finish)
    delta: float                 # technology trajectory (-1..+1)

    # Health (W)
    phi: float                   # physical health (1..5)
    psi: float                   # mental health (1..5)
    zeta: float                  # fitness practice (0..4)
    eta: float                   # net emotional impact, signed (-2..+2)
    nu: float                    # relational quality (1..4)

    # User-provided thresholds (for viable/desirable checks)
    emergency_fund_floor: float
    desired_income_min: float


_FITNESS_MAP = {"none": 0, "occasional": 1, "weekly": 3, "near_daily": 4}
_EMOTIONAL_MAP = {
    "very_negative": -2, "negative": -1, "neutral": 0,
    "positive": 1, "very_positive": 2,
}
_RELATIONAL_MAP = {"thin": 1, "okay": 2, "strong": 3, "very_strong": 4}
_PRESSURE_MAP = {"zero": 5, "mild": 4, "moderate": 3, "high": 2}
_CAREER_FEELING_MAP = {
    "thriving": 5, "engaged": 4, "drifting": 3, "surviving": 2, "miserable": 1,
}
# Felt domestic alignment as a function of relationship status. The
# midlife model treats i3 as alignment of the household with the life
# being built, not as residential autonomy from parents. Singles are
# assumed to be aligned with their own household by default.
_REL_STATUS_I3 = {
    "single": 4.0, "dating": 4.0,
    "partnered": 4.0, "married": 4.0,
    "separated": 2.0, "divorced": 3.0, "widowed": 3.0,
    "complicated": 2.5,
}


def _scale(value: Any, default: float = 3.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def derive_life_state(answers: dict[str, Any]) -> LifeStateV1:
    take_home = _scale(answers.get("current_monthly_take_home"), 0.0)
    bills = _scale(answers.get("current_monthly_bills"), 0.0)
    cash_flow = take_home - bills
    liquid = _scale(answers.get("current_savings"), 0.0)
    retirement = _scale(answers.get("retirement_savings"), 0.0)
    savings_total = liquid + retirement
    debt = _scale(answers.get("current_debt"), 0.0)

    # r tracks short-horizon resilience — how many months the *liquid*
    # buffer covers. Retirement accounts inflate sigma but not r.
    monthly_overhead = max(bills, 1.0)
    risk_buffer_months = liquid / monthly_overhead

    # i1 (mobility): default neutral — most midlifers have a car and the
    # binding mobility question is geographic flexibility, not vehicle
    # ownership. Move intent raises it; aging-parent caregiving lowers it.
    i1 = 3.0
    wants_place = answers.get("wants_place") or []
    if "move_city" in wants_place or "move_country" in wants_place:
        i1 = 4.0
    if answers.get("has_dependents") in ("aging_parents", "kids_and_parents"):
        i1 = max(1.0, i1 - 1.0)

    # i2 (financial independence): cash-flow + buffer signal.
    if cash_flow > 1500:
        i2 = 4.0
    elif cash_flow > 0:
        i2 = 3.0
    else:
        i2 = 1.0
    if _scale(answers.get("current_debt"), 0.0) > savings_total > 0:
        i2 = max(1.0, i2 - 1.0)

    # i3 (domestic alignment): relationship_status sets the floor;
    # partner alignment (when collected) modulates.
    rel_status = str(answers.get("relationship_status") or "single")
    i3 = _REL_STATUS_I3.get(rel_status, 3.0)
    pa = _scale(answers.get("partner_alignment"), 0.0)
    if pa:
        # 1..5 scale, centered: <3 drags i3 down, >3 lifts it
        i3 = max(0.0, min(5.0, i3 + (pa - 3.0) * 0.5))

    # i4 (decision independence): how the user feels about their work
    # plus monthly money pressure tolerance. Career_feeling is the
    # primary signal — drifting / surviving / miserable scores low.
    cf = str(answers.get("career_feeling") or "engaged")
    i4 = float(_CAREER_FEELING_MAP.get(cf, 3))
    pressure_pref = float(_PRESSURE_MAP.get(answers.get("monthly_pressure_comfort", ""), 3))
    i4 = (i4 + pressure_pref) / 2.0

    # e (enjoyment): emotional state lifts e by a base; career_feeling
    # adds a smaller modifier; creative_practice adds a small lift.
    base_emotional = _EMOTIONAL_MAP.get(answers.get("emotional_state_now", "neutral"), 0)
    e = float(base_emotional + 2)  # 0..4
    cp = str(answers.get("creative_practice_freq") or "none")
    if cp in ("weekly", "near_daily"):
        e = min(5.0, e + 0.5)

    # g (goal progress): completion confidence is the primary explicit
    # signal; ready_for_change adds a small lift since readiness implies
    # felt direction.
    g = _scale(answers.get("completion_confidence"), 3.0)
    ready = _scale(answers.get("ready_for_change"), 0.0)
    if ready >= 4:
        g = min(5.0, g + 0.5)

    # beta (stability): user's self-reported stability_now. Divorce
    # in-process or recent drags it down somewhat.
    beta = _scale(answers.get("stability_now"), 3.0)
    ds = str(answers.get("divorce_status") or "not_applicable")
    if ds in ("considering", "in_process"):
        beta = max(1.0, beta - 1.0)
    elif ds == "recent":
        beta = max(1.0, beta - 0.5)

    # K — capability path. If wants_education has nothing or only
    # "no_formal_training", K is parked; otherwise the explicit answers
    # set the relevant fields.
    k_path = str(answers.get("education_modality") or "none")
    tau = _scale(answers.get("max_training_months"), 0.0)
    mu = _scale(answers.get("training_budget"), 0.0)
    completion = _scale(answers.get("completion_confidence"), 3.0)
    rho = max(0.0, 1.0 - completion / 5.0)

    # Sleep is a midlife-specific signal that modulates phi and psi.
    sleep = _scale(answers.get("sleep_quality"), 3.0)
    phi = _scale(answers.get("physical_health_self"), 3.0)
    psi = _scale(answers.get("mental_health_self"), 3.0)
    # Bad sleep drags both — capped so a single bad answer can't dominate.
    if sleep <= 2:
        phi = max(1.0, phi - 0.5)
        psi = max(1.0, psi - 0.5)

    # eta: net emotional impact uses career_feeling and emotional_state
    # together. The dominant signal is whichever is more negative —
    # midlife emotional drift often shows up first in work and only
    # later in general affect.
    cf_eta = (_CAREER_FEELING_MAP.get(cf, 3) - 3) / 2.0   # → -1..+1
    state_eta = float(base_emotional)                      # → -2..+2
    eta = (cf_eta + state_eta) / 2.0
    # Burnout / mental-health investment intent is itself a signal that
    # eta is negative; if the user marked it, floor eta at -0.5 so it
    # shows up in the prompt.
    health_wants = answers.get("wants_health") or []
    if "recovery_from_burnout" in health_wants or "mental_health_support" in health_wants:
        eta = min(eta, -0.5)

    nu = float(_RELATIONAL_MAP.get(answers.get("relational_quality_now", "okay"), 2))

    return LifeStateV1(
        i1=i1, i2=i2, i3=i3, i4=i4,
        e=e,
        g=g,
        beta=beta,
        p=_scale(answers.get("productive_hours_per_week"), 0.0),
        b=_scale(answers.get("buffer_hours_per_week"), 0.0),
        q=_scale(answers.get("quality_of_time_now"), 3.0),
        c=cash_flow,
        sigma=savings_total,
        d=debt,
        r=risk_buffer_months,
        y=take_home,
        gamma=0.03,  # default annual growth; refined by research
        k=k_path,
        tau=tau,
        mu=mu,
        rho=rho,
        delta=0.0,  # default neutral; refined by research
        phi=phi,
        psi=psi,
        zeta=float(_FITNESS_MAP.get(answers.get("fitness_practice_freq", "occasional"), 1)),
        eta=eta,
        nu=nu,
        emergency_fund_floor=_scale(answers.get("emergency_fund_floor"), 0.0),
        desired_income_min=_scale(answers.get("desired_two_year_income"), 0.0),
    )


# ---------------------------------------------------------------------------
# Path scoring — same math as build-independence v0_5_0, with midlife
# defaults for the per-stage cost models.
# ---------------------------------------------------------------------------


# Conservative cost defaults used when research data is unavailable.
# Midlife-tuned: training cost and time are larger because the typical
# midlife training is a credential or program, not a high-school job.
DEFAULT_TRAINING_TIME_PER_WEEK = 12.0   # hours — part-time evenings/weekends
DEFAULT_MOVE_OVERHEAD_MONTHLY = 200.0   # short-term move friction (storage, double-rent, etc.)

# Viable-state floors. Midlife thresholds:
P_MIN = 4.0       # productive hours — lower than teen since obligations are higher
B_MIN = 2.0       # buffer hours
Q_MIN = 2.0       # quality (1..5)
PHI_MIN = 2.0     # physical health
PSI_MIN = 2.0     # mental health
NU_MIN = 1.5      # relational quality (1..4) — slightly above teen floor

# Desirable-state floors. Strictly above viable.
I_MIN = 2.0
E_MIN = 2.0
G_MIN = 2.0
BETA_MIN = 2.0
ZETA_MIN = 1.0
ETA_MIN = -0.5    # signed; midlife model treats persistent negative eta seriously


@dataclass
class StageResult:
    id: str
    label: str
    duration_months: float
    life_state: LifeStateV1
    viable: bool
    desirable: bool
    fails: list[str]
    momentum: float
    recoverability: float
    decision_inputs: dict[str, float]


@dataclass
class PathResult:
    id: str
    label: str
    description: str
    bucket: str
    stages: list[StageResult]
    path_momentum: float
    viable: bool
    terminal_desirable: bool
    min_recoverability: float

    @property
    def fails(self) -> list[str]:
        out: list[str] = []
        if not self.viable:
            out.append("at least one stage is not viable")
        if not self.terminal_desirable:
            out.append("terminal stage is not desirable")
        return out


def _apply_stage_modifiers(base: LifeStateV1, stage: dict[str, Any]) -> LifeStateV1:
    """Project the baseline L through a stage's structural flags."""
    p = base.p
    c = base.c
    sigma = base.sigma
    y = base.y
    eta = base.eta
    i1 = base.i1

    if stage.get("training_active"):
        p = max(0.0, p - DEFAULT_TRAINING_TIME_PER_WEEK)
        if stage.get("duration_months", 0) > 0:
            sigma -= base.mu * (stage["duration_months"] / max(base.tau, stage["duration_months"]))

    if stage.get("moves_out"):
        # At midlife "moves_out" represents a residential change rather
        # than first-time independence. The cost is short-term move
        # overhead, not net new rent (rent is already in current_monthly_bills).
        c -= DEFAULT_MOVE_OVERHEAD_MONTHLY
        i1 = min(5.0, i1 + 1.0)

    if stage.get("income_growth"):
        y = y * 1.20  # 20% lift after a credential or successful pivot
        c = y - max(base.y - base.c, 0.0)  # keep prior bills, new income

    sigma_after = max(0.0, sigma + c * stage.get("duration_months", 0))
    r_after = sigma_after / max(base.y - c + 1.0, 1.0)

    # eta drift: training-only stages drag eta down slightly; income
    # growth lifts it; pure repair / sabbatical stages (income flat,
    # no training) hold eta steady.
    if stage.get("training_active") and not stage.get("income_growth"):
        eta = max(eta - 0.2, -2.0)
    if stage.get("income_growth"):
        eta = min(eta + 0.4, 2.0)

    return LifeStateV1(
        **{**base.__dict__, "p": p, "c": c, "sigma": sigma_after,
           "r": r_after, "y": y, "eta": eta, "i1": i1}
    )


def _check_viable(L: LifeStateV1) -> list[str]:
    fails: list[str] = []
    if L.c < 0:
        fails.append(f"negative cash flow (${L.c:,.0f}/mo)")
    if L.emergency_fund_floor > 0 and L.sigma < L.emergency_fund_floor:
        fails.append(f"savings below floor (${L.sigma:,.0f} < ${L.emergency_fund_floor:,.0f})")
    if L.r < 1.5:
        fails.append(f"buffer below 1.5 months ({L.r:.1f})")
    if L.p < P_MIN:
        fails.append("too little productive time")
    if L.b < B_MIN:
        fails.append("too little buffer time")
    if L.q < Q_MIN:
        fails.append("low time quality")
    if L.phi < PHI_MIN:
        fails.append("physical health below floor")
    if L.psi < PSI_MIN:
        fails.append("mental health below floor")
    if L.nu < NU_MIN:
        fails.append("relational quality below floor")
    return fails


def _check_desirable_extras(L: LifeStateV1) -> list[str]:
    fails: list[str] = []
    if L.i1 < I_MIN: fails.append("location agency below desirable")
    if L.i2 < I_MIN: fails.append("financial independence below desirable")
    if L.i3 < I_MIN: fails.append("domestic alignment below desirable")
    if L.i4 < I_MIN: fails.append("decision independence below desirable")
    if L.e < E_MIN: fails.append("enjoyment below desirable")
    if L.g < G_MIN: fails.append("goal progress below desirable")
    if L.beta < BETA_MIN: fails.append("stability below desirable")
    if L.desired_income_min > 0 and L.y < L.desired_income_min:
        fails.append(f"income below your desired ${L.desired_income_min:,.0f}")
    if L.sigma < L.d:
        fails.append("debt exceeds savings")
    if L.zeta < ZETA_MIN: fails.append("fitness practice below desirable")
    if L.eta < ETA_MIN: fails.append("emotional impact too negative")
    return fails


def _saturate(x: float, lo: float = 0.0, hi: float = 5.0) -> float:
    return max(lo, min(hi, x))


def _momentum(L: LifeStateV1, weights: dict[str, float]) -> float:
    """§2.5 Momentum(L). Includes the q·e cross-term plus a linear sum."""
    score = weights.get("qe", 5.0) * (L.q / 5.0) * (L.e / 5.0) * 5.0
    components = {
        "i1": _saturate(L.i1), "i2": _saturate(L.i2),
        "i3": _saturate(L.i3), "i4": _saturate(L.i4),
        "e": _saturate(L.e),
        "g": _saturate(L.g), "beta": _saturate(L.beta),
        "p": _saturate(L.p / 8.0),       # 40 hrs/wk = 5
        "b": _saturate(L.b / 4.0),       # 20 hrs/wk = 5
        "q": _saturate(L.q),
        "c": _saturate(L.c / 1500.0),    # $7.5k/mo cash flow = 5 (midlife scale)
        "sigma": _saturate(L.sigma / 50000.0),  # $250k savings = 5
        "r": _saturate(L.r),             # 5 months buffer = 5
        "y": _saturate(L.y / 2000.0),    # $10k/mo household income = 5
        "gamma": _saturate(L.gamma * 50.0),    # 10% growth = 5
        "phi": _saturate(L.phi), "psi": _saturate(L.psi),
        "zeta": _saturate(L.zeta * 1.25),      # 0..4 → 0..5
        "eta": _saturate((L.eta + 2.0) * 1.25),  # -2..+2 → 0..5
        "nu": _saturate(L.nu * 1.25),    # 1..4 → 1..5
    }
    for k, v in components.items():
        score += weights.get(k, 0.0) * v
    return score


def _recoverability(stage_inputs: dict[str, float], rec_weights: dict[str, float]) -> float:
    """§2.4 R(s_j) = 1 - weighted(λ, ξ, Δ)."""
    lam = float(stage_inputs.get("lambda", 0.0))
    xi = float(stage_inputs.get("xi", 0.0))
    disrupt = float(stage_inputs.get("state_disruption", 0.0))
    w_l = float(rec_weights.get("lambda", 1.0))
    w_x = float(rec_weights.get("xi", 1.0))
    w_d = float(rec_weights.get("delta", 1.0))
    total = w_l + w_x + w_d
    if total <= 0:
        return 1.0
    return max(0.0, 1.0 - (w_l * lam + w_x * xi + w_d * disrupt) / total)


def score_path(
    path: dict[str, Any],
    base: LifeStateV1,
    weights: dict[str, float],
    rec_weights: dict[str, float],
) -> PathResult:
    L = base
    stage_results: list[StageResult] = []
    path_momentum = 0.0
    all_viable = True
    min_R = 1.0

    for stage in path["stages"]:
        L = _apply_stage_modifiers(L, stage)
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
        stage_results.append(StageResult(
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
        ))

    terminal = stage_results[-1].desirable if stage_results else False
    return PathResult(
        id=path["id"],
        label=path["label"],
        description=path.get("description", ""),
        bucket=path.get("bucket", "compounding_change"),
        stages=stage_results,
        path_momentum=path_momentum,
        viable=all_viable,
        terminal_desirable=terminal,
        min_recoverability=min_R,
    )


def _life_state_dict(L: LifeStateV1) -> dict[str, Any]:
    """JSON-serializable view used in plan-meta and the prompt context."""
    return {
        "V": {"i1": L.i1, "i2": L.i2, "i3": L.i3, "i4": L.i4,
              "e": L.e, "g": L.g, "beta": L.beta},
        "T": {"p": L.p, "b": L.b, "q": L.q},
        "A": {"c": round(L.c, 0), "sigma": round(L.sigma, 0), "d": round(L.d, 0),
              "r_months": round(L.r, 1), "y": round(L.y, 0), "gamma": L.gamma},
        "K": {"k": L.k, "tau": L.tau, "mu": L.mu, "rho": round(L.rho, 2), "delta": L.delta},
        "W": {"phi": L.phi, "psi": L.psi, "zeta": L.zeta,
              "eta": round(L.eta, 2), "nu": L.nu},
        "thresholds": {
            "emergency_fund_floor": L.emergency_fund_floor,
            "desired_income_min": L.desired_income_min,
        },
    }


# ---------------------------------------------------------------------------
# Logic class
# ---------------------------------------------------------------------------


class Logic(BaseLogic):
    REVISION_DIR = Path(__file__).resolve().parent

    def __init__(self, pack: Any) -> None:
        super().__init__(pack)
        self._raw = yaml.safe_load((self.REVISION_DIR / "scenarios.yaml").read_text())
        self._horizon_months = int(self._raw.get("horizon_months", 60))
        self._paths_raw = self._raw.get("paths", [])
        self._rec_weights = (
            yaml.safe_load((self.REVISION_DIR / "weights.yaml").read_text())
            .get("recoverability_weights", {})
        )

    def compute_life_state(self, answers: dict[str, Any]) -> LifeStateV1:
        return derive_life_state(answers)

    def score(self, life: LifeStateV1, research_data: dict[str, Any]) -> list[PathResult]:
        scored = [
            score_path(p, life, self.pack.weights, self._rec_weights)
            for p in self._paths_raw
        ]
        scored.sort(
            key=lambda r: (r.viable and r.terminal_desirable, r.path_momentum),
            reverse=True,
        )
        return scored

    def life_state_to_meta(self, life: LifeStateV1) -> dict[str, Any]:
        return _life_state_dict(life)

    def scored_to_meta(self, scored: list[PathResult]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for r in scored:
            out.append({
                "id": r.id,
                "label": r.label,
                "bucket": r.bucket,
                "viable": r.viable,
                "terminal_desirable": r.terminal_desirable,
                "fails": r.fails,
                "path_momentum": round(r.path_momentum, 1),
                "min_recoverability": round(r.min_recoverability, 2),
                "stages": [
                    {
                        "id": s.id,
                        "label": s.label,
                        "duration_months": s.duration_months,
                        "viable": s.viable,
                        "desirable": s.desirable,
                        "fails": s.fails,
                        "momentum": round(s.momentum, 1),
                        "recoverability": round(s.recoverability, 2),
                        "life_state": _life_state_dict(s.life_state),
                    }
                    for s in r.stages
                ],
            })
        return out

    def build_plan_context(
        self,
        *,
        profile: Any,
        answers: dict[str, Any],
        life: LifeStateV1,
        scored: list[PathResult],
        research_data: dict[str, Any],
        chat_context: str,
    ) -> dict[str, Any]:
        from pathwise.core.plan import _format_answer, _pretty_json, _question_views

        # Midlife buckets — replaces the build-independence triple of
        # fast_freedom / compounding_freedom / skill_leverage.
        paths_by_bucket: dict[str, list[PathResult]] = {
            "bold_change": [],
            "compounding_change": [],
            "creative_reinvention": [],
        }
        for r in scored:
            paths_by_bucket.setdefault(r.bucket, []).append(r)

        return {
            "profile": profile,
            "answers": answers,
            "questions": _question_views(self.pack, answers),
            "life_state": _life_state_dict(life),
            "research_json": _pretty_json(research_data),
            "scored_paths": scored,
            "paths_by_bucket": paths_by_bucket,
            "horizon_months": self._horizon_months,
            "format_answer": _format_answer,
            "chat_context": chat_context,
        }


def make_logic() -> Logic:
    return Logic.make()
