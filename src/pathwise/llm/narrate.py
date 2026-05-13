"""LLM narrator for the path sandbox.

The sandbox flips the old plan generator on its head: instead of the LLM
producing the answer, the *user* drives the math (sliders for stage
durations, rho, delta, costs) and the LLM narrates what they discovered.

The narrator is grounded in the simulation result, not in the user's
intent. It:

* names which paths went red and which constraint failed
* names which paths sit on the Pareto frontier and what tradeoff they
  represent (high momentum vs high recoverability)
* names what changed if the user has a specific focus question (e.g.
  "what happened when I dropped rho to 0?")
* refuses to recommend. The user is the one making the discovery.

Sonnet 4.6 with thinking disabled and effort low — same posture as chat.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pathwise.llm.client import call_chat

logger = logging.getLogger(__name__)


_NARRATOR_SYSTEM_SUFFIX = """

## Sandbox mode

The user is interacting with a sandbox UI in front of the math. They move
sliders (stage durations, completion risk $\\rho$, technology trajectory
$\\delta$, rent, car overhead, $R_{min}$). After each move, the simulator
re-runs and returns the path scores. **Your job is to narrate what they
just discovered, not to recommend.**

Be specific about which path, which stage, which constraint. Cite numbers
from the result. Two sentences per observation, three at most. No
preamble. No "great question". Talk to the user, not about them.

If a path went non-viable, name the failing constraint: which stage
failed, on which floor (cash flow $c < 0$, risk buffer $r < r_{min}$,
productive time $p < p_{min}$, health floor, etc.).

If a path lost the Pareto frontier, name what beat it on both axes.

If Monte Carlo ran, refer to the percentile bands ($P_{10}$/$P_{50}$/$P_{90}$)
and the viability probability — not the deterministic point estimate alone.

End by naming the next slider the user could move to test what they're
curious about, framed as a question they can answer themselves. Do not
state which path is best.
"""


def _path_summary(path: dict[str, Any]) -> dict[str, Any]:
    """Compact JSON view per path so the LLM context isn't bloated."""
    mc = path.get("monte_carlo")
    out: dict[str, Any] = {
        "id": path["id"],
        "label": path["label"],
        "bucket": path["bucket"],
        "enabled": path["enabled"],
        "viable": path["viable"],
        "terminal_desirable": path["terminal_desirable"],
        "on_pareto_frontier": path["on_pareto_frontier"],
        "r_min_satisfied": path["r_min_satisfied"],
        "path_momentum": path["path_momentum"],
        "min_recoverability": path["min_recoverability"],
        "rho_used": round(float(path["rho_used"]), 3),
        "delta_used": round(float(path["delta_used"]), 3),
        "stages": [
            {
                "id": s["id"],
                "label": s["label"],
                "duration_months": s["duration_months"],
                "viable": s["viable"],
                "fails": s.get("fails", [])[:3],
                "momentum": s["momentum"],
                "recoverability": s["recoverability"],
                "cash_flow_monthly": s["cash_flow_monthly"],
                "risk_buffer_months": s["risk_buffer_months"],
            }
            for s in path.get("stages", [])
        ],
    }
    if mc:
        out["monte_carlo"] = {
            "samples": mc["samples"],
            "viable_prob": round(float(mc["viable_prob"]), 2),
            "terminal_desirable_prob": round(float(mc["terminal_desirable_prob"]), 2),
            "momentum_p10": round(float(mc["momentum_p10"]), 1),
            "momentum_p50": round(float(mc["momentum_p50"]), 1),
            "momentum_p90": round(float(mc["momentum_p90"]), 1),
            "min_r_p10": round(float(mc["min_r_p10"]), 2),
            "min_r_p90": round(float(mc["min_r_p90"]), 2),
        }
    return out


def narrate_discovery(
    *,
    profile: Any,
    pack: Any,
    life_state_meta: dict[str, Any],
    result_json: dict[str, Any],
    focus: str | None,
    model: str,
) -> str:
    """Stream a single narration turn from the LLM, grounded in the result."""
    paths_summary = [_path_summary(p) for p in result_json.get("paths", [])]
    frontier = result_json.get("pareto_frontier", [])
    r_min = result_json.get("r_min", 0.4)
    horizon = result_json.get("horizon_months", 60)

    system_prompt = pack.prompt_path("system").read_text() + _NARRATOR_SYSTEM_SUFFIX

    payload = {
        "first_name": profile.first_name,
        "horizon_months": horizon,
        "r_min": r_min,
        "baseline_life_state": life_state_meta,
        "paths": paths_summary,
        "pareto_frontier_ids": frontier,
    }
    body = json.dumps(payload, indent=2)
    if focus:
        user_prompt = (
            f"{profile.first_name} is exploring the sandbox. They asked: "
            f"\"{focus.strip()}\"\n\n"
            f"Here is the current simulation result:\n\n```json\n{body}\n```\n\n"
            "Narrate what just happened in the math. Be specific about which path "
            "and which constraint. Name the tradeoff. Do not recommend a path. "
            "End with a slider they could move next to test the question they care about."
        )
    else:
        user_prompt = (
            f"{profile.first_name} just moved a slider in the sandbox. "
            f"Here is the current simulation result:\n\n```json\n{body}\n```\n\n"
            "Narrate the single most surprising or load-bearing finding visible "
            "in this state — what's on the Pareto frontier, what's non-viable and "
            "why, or what shifted across paths. Two short paragraphs max. End "
            "with one specific slider they could move next."
        )

    result = call_chat(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        model=model,
        max_tokens=1024,
    )
    return result.text
