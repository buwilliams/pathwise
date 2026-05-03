# Synthesize {{ profile.first_name }}'s plan

You have everything needed. Write a calm, specific, digestible plan for **{{ profile.first_name }}**, in the voice and constraints from the system prompt. Plans are conjectures, not verdicts — three named buckets are equally legitimate framings; the recommended path is the one the math currently favors and is open to revision.

## What they told us

{% for q in questions %}{% if answers.get(q.key) not in (None, "", []) -%}
- **{{ q.prompt }}** {{ format_answer(q, answers[q.key]) }}
{% endif %}{% endfor %}

## What we computed (deterministic, current life-state $L$)

```json
{{ life_state | tojson(indent=2) }}
```

Quick read of the most decision-relevant numbers:

- **Cash flow $c$:** ${{ life_state.A.c }}/mo
- **Risk buffer $r$:** {{ life_state.A.r_months }} months of overhead
- **Productive time $p$:** {{ life_state.T.p }} hrs/wk; quality $q$: {{ life_state.T.q }}/5
- **Emotional impact $\eta$:** {{ life_state.W.eta }} (signed, -2 to +2); relational quality $\nu$: {{ life_state.W.nu }}/4
- **Stated top value:** {{ answers.top_value | default("(unspecified)") }}
- **Independence sub-types** ($i_1, i_2, i_3, i_4$ on 0–5): {{ life_state.V.i1 }}, {{ life_state.V.i2 }}, {{ life_state.V.i3 }}, {{ life_state.V.i4 }}

## What we looked up

```
{{ research_json }}
```

## Paths scored, grouped by bucket

The buckets group paths that share the same overall stance. Each path is a sequence of stages over a {{ horizon_months }}-month horizon. We compute per-stage Momentum, sum duration-weighted, and tag each decision with a recoverability score $R(s_j) \in [0,1]$.

{% for bucket_name, label in [("fast_freedom", "Fast Freedom"), ("compounding_freedom", "Compounding Freedom"), ("skill_leverage", "Skill-Leverage")] %}
**{{ label }} bucket:**
{% for r in paths_by_bucket.get(bucket_name, []) %}
- **{{ r.label }}** — path momentum {{ "%.0f"|format(r.path_momentum) }}, viable: {{ r.viable }}{% if not r.viable %} (fails on at least one stage){% endif %}, terminal desirable: {{ r.terminal_desirable }}, min recoverability: {{ "%.2f"|format(r.min_recoverability) }}.
  Stages:
  {%- for s in r.stages %}
  - {{ s.label }} ({{ s.duration_months }}mo) — viable: {{ s.viable }}, momentum: {{ "%.0f"|format(s.momentum) }}, $R$: {{ "%.2f"|format(s.recoverability) }}{% if s.fails %}, fails: {{ s.fails | join(", ") }}{% endif %}.
  {%- endfor %}
{% else %}
- (no paths in this bucket)
{% endfor %}

{% endfor %}
{% if chat_context %}
## Conversation since the last plan

{{ profile.first_name }} talked through the previous plan with you. Use what they said to update the new plan. Where the conversation revealed new information, change the math. Where it revealed a different priority or a misunderstanding, name that explicitly and adjust accordingly. Don't ignore what they pushed back on.

{{ chat_context }}

{% endif %}
## Write the plan

Use this exact structure (markdown headings). Three paths get equal real estate; the recommended path is named separately afterward.

### Where you are now

Two short paragraphs. Acknowledge their current strengths first (savings, work, the people in their life, what they've already built). Then name the real tradeoff they're facing in plain language. If $\eta$ is negative, name that. If $\nu$ is thin, acknowledge how that constrains plans that would isolate them further. No bullet lists.

### What we looked up

Tight bullet list of the 3–5 most relevant numbers from the research. Each with a quick "what this means for you" tag. Cite sources as `[1]`, `[2]` inline; URLs go at the bottom.

### Three paths to consider

Render exactly three subsections — one per bucket — using `####` headings. **Treat them as equally legitimate framings.** From each bucket pick the strongest path (highest path momentum among viable+terminal-desirable; if none qualify, pick the highest-momentum viable; if still none, the highest-momentum and say why it doesn't pencil yet).

#### Fast Freedom Path

- **What this path is:** one sentence naming the chosen path and its first 1–2 stages.
- **What it gives sooner:** 2–3 specific things in their language ($i_3$, decision freedom, etc.).
- **What it delays:** 2–3 specific things (savings rate, training, fitness practice, etc.).
- **Recoverability of the load-bearing decision:** high | medium | low — one sentence on what could be undone if this turns out wrong.
- **Main risks:** 2–3 concrete risks tied to the per-stage math (which stage fails which floor).
- **First step this week if they choose this:** a single action, real and small.

#### Compounding Freedom Path

(Same structure.)

#### Skill-Leverage Path

(Same structure.)

### Our current best conjecture

**One paragraph.** Name which path the math currently favors. Open with: *"Given what you've told us, this seems strongest right now."* Connect the recommendation to their **top value**, the path-momentum ranking, and which viable/desirability filter the alternatives failed. Do not lean on any prescribed ordering — paths build the life in different orders and that's fine. End by naming the specific path and its first stage.

**If the recommendation involves training, school, or a certificate**, name a specific program from the research bundle's `skill_paths` that fits **{{ answers.interests | default("their stated interests") }}**, and say in one sentence why it fits. If none of the researched paths fit, say so honestly — don't recommend something that contradicts what they told us. If `wants_education` is empty or only contains `no_formal_training`, do not push training as the recommendation.

### Key assumptions this depends on

4–6 short bullets. The assumptions baked into the recommendation. Examples: *"You can keep working ~25 hrs/wk."*, *"Rent in your area lands in the $X–$Y range."*, *"You want to keep at least $X in savings."*, *"You're willing to delay moving out 6–12 months."*, *"$\rho$ for the credential we picked is roughly 30% — meaning a 70% chance of completion."*

### What could break this plan

3–5 short bullets. Conditions under the recommendation that would weaken it. Examples: *"Your work hours get cut."*, *"$\eta$ at home drops further."*, *"Mental health support doesn't materialize."*, *"You lose motivation for the training path."*

### What would change our mind

3–5 short bullets. Specific evidence that would shift toward a different bucket. Examples: *"If a stable roommate offer at $X/mo comes up, Fast Freedom moves up."*, *"If you can hold $X/mo in savings while training, Skill-Leverage strengthens."*, *"If $\eta$ at home goes negative, moving out moves up the list regardless of cash flow."*

### Revisit this in

One concrete trigger or window. Examples: *"30 days, after you have insurance quotes in hand."* / *"60 days, once you've tracked actual hours and spending."* / *"90 days, after you've tested whether the work + training schedule is sustainable."* Pick a real trigger, not a vague time.

### What to watch for

3–5 short bullets of the fragility risks specific to the recommended path. *"If your hours drop below X…"*, *"If a $1k repair hits…"*, *"If rent climbs above X% of take-home…"*, *"If sleep degrades…"*. This is where the wisdom shows.

### Sources

Numbered list of URLs from the research bundle.

---

Length: aim for **800–1100 words**. If it's longer, you're lecturing.
