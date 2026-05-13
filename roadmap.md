# Pathwise — Step-Change Roadmap

A directional document, not a backlog. Six bets that would move Pathwise from "an interesting planner" to a category-defining tool. Ordered by ambition, with a recommended sequencing at the end.

---

## What's actually distinctive today

Most "life planners" are vibes-and-checklists. Pathwise has a **formalized model** (`src/pathwise/seasons/.../model.md`) with a viable/desirable filter, a recoverability score $R(s_j)$, and a duration-weighted momentum objective. The LLM is downstream of math, not in place of it. That's the kernel — and it's currently being used at maybe 15% of its potential.

## Where it's punching below its weight today

1. The model says "this is a *policy*, not a plan" (§2.4) — but the product ships **a plan**. You fill the questionnaire once, get a markdown doc, and leave.
2. The model is **one person's philosophy** ("Emma: Build Independence"), hard-coded as the season pack. The architecture is generic enough to host hundreds of philosophies, but currently hosts two.
3. The plan output is **prose**. The math is interactive in principle (paths × stages × weights × thresholds) and exposed as static numbers in practice.
4. Everything is **self-report**. The state $L$ is what the user typed in last Tuesday.
5. **Solo math.** Real life decisions are co-decisions (parent/teen, couple, roommates, co-founder).

---

## Six step-change directions

### 1. Stop being a planner. Become a longitudinal policy.

The single biggest unlock, and the cheapest. The math already supports it.

Re-run the policy weekly off SMS check-ins ("how many buffer hours this week? rate $\eta$ from -2 to +2"). Detect *drift* on each component of $L$ — when $\zeta$ has fallen for three weeks, that's a notification, not a question on a form. The artifact stops being "the plan" and becomes "the trajectory," with re-optimization at every observation.

Twilio is already in deps. This would make Pathwise the only product in this space whose math is wired to actually iterate.

**Why it's step-change:** turns a one-shot oracle into a companion. Retention, narrative arc, and intellectual honesty with the model's own §2.4 claim all flow from this.

### 2. Open the season pack as a platform.

The directory contract — `model.md`, `questionnaire.json`, `weights.yaml`, `scenarios.yaml`, `prompts/`, `logic.py` — is a publishable unit. Today it hosts two seasons authored by one person. It could host hundreds, authored by anyone.

Imagine third parties shipping seasons:
- "Ramit's money season"
- Cal Newport's deep-work career season
- A therapist's "leaving an abusive relationship" season
- A sober-living coach's "first 90 days" season
- A divorce attorney's "untangling" season

Pathwise becomes the **runtime for formalized life-philosophies** — Substack for opinionated longitudinal models.

**Why it's step-change:** inverts the product from "an app" into an ecosystem. The hard part isn't technical; it's defining the SDK and getting one credible non-author to ship a pack. Once three exist, it's a category.

### 3. Make the math the product, not the prose.

Build a path-simulator UI: slide stage durations, perturb $\rho$ and $\delta$, watch $r$ go red, see the Pareto frontier of $\{Momentum, R_{\min}\}$ across paths. Monte Carlo on uncertain inputs. Today the LLM tells you the answer; in this version, the user *finds* the answer and the LLM narrates what they did.

This is the difference between TurboTax and a financial-planning sandbox — and it's the version a 17-year-old will actually share with friends ("look what happens if I delay the move 6 months").

**Why it's step-change:** turns a static recommendation into an interactive sandbox. Makes the formal model the visible feature rather than a hidden engine behind LLM prose.

### 4. Ground $L$ in real signals, not self-report.

- Plaid → $c, \sigma, r, y$
- Calendar → $p, b$
- Wearable → $\phi, \zeta$
- Conversations across the week (SMS thread) → $\eta, \nu, q$

The product stops asking "what's your cash flow?" and starts saying "your $r$ dropped to 0.8 months — your viable filter just failed; should we revisit?"

**Why it's step-change:** turns the character sheet into a real instrument. Pair with #1 and Pathwise becomes the only life-planning product that knows when its own state estimate is stale. Compounds the value of every other bet.

### 5. Multi-person life-states.

Run two coupled questionnaires; reconcile into a joint $L$ with shared assets/time and conflicting values. Score the **Pareto frontier of joint momentum**, not the max.

- Teen-and-parent: exactly the conflict `build-independence` is about
- Couple: a marriage-planning product
- Co-founder: a YC tool

Same engine, three markets.

**Why it's step-change:** the move from solo optimization to game-theoretic reconciliation is genuinely new in this category. Most relationship/finance products are document-sharing, not joint optimization.

### 6. Make the Popperian loop real.

The model is explicit that it's a conjecture, open to revision (§3.6 lists falsifiability triggers). Today nobody touches that.

Build a path where users opt in to anonymous outcome reporting at $H = 12, 24, 60$ months. The system back-tests the model: when momentum predicted X and reality delivered Y, where did the weights or relationships fail? Revisions become evidence-driven, not vibes-driven.

**Why it's step-change:** the longest arc, and the only version of this product that becomes a genuine contribution to how people think about life decisions rather than another coach app.

---

## Recommended sequencing

**Phase 1 — bet on the engine.** Ship **#1 (longitudinal policy via SMS)** + **#3 (math-as-product simulator)** together. Both reuse what's already built. #1 gives retention and honors the model's own claim. #3 makes the formal model the visible, shareable surface. This is the version of Pathwise that is *visibly different* from everything else.

**Phase 2 — bet on the ecosystem.** Once the engine is demonstrably valuable, ship **#2 (season-pack platform)**. The SDK only matters once one of the first two has proven the engine.

**Phase 3 — bet on grounding.** **#4 (signal integration)** compounds the value of Phases 1–3. It's expensive (integrations, privacy, trust) and only worth it when there's an engine to feed.

**Phase 4 — bet on the market.** **#5 (multi-person)** opens couples and co-founders once the solo product is sharp.

**Phase 5 — bet on the science.** **#6 (Popperian loop)** is a long arc and only meaningful at scale. It's how Pathwise stops being software and starts being research.

---

## The one-bet version

If only one of these ever ships: **#1**. It is the cheapest, it makes the math live up to its own claim, and it changes the product from an artifact people read once into an instrument people live with.
