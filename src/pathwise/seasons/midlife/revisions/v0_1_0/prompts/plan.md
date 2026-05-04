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
- **Risk buffer $r$:** {{ life_state.A.r_months }} months of liquid overhead
- **Productive time $p$:** {{ life_state.T.p }} hrs/wk; quality $q$: {{ life_state.T.q }}/5
- **Emotional impact $\eta$:** {{ life_state.W.eta }} (signed, -2 to +2); mental health $\psi$: {{ life_state.W.psi }}/5; relational quality $\nu$: {{ life_state.W.nu }}/4
- **Stated top value:** {{ answers.top_value | default("(unspecified)") }}
- **Readiness for change:** {{ answers.ready_for_change | default("(unspecified)") }}/5; biggest block: {{ answers.biggest_block | default("(unspecified)") }}
- **Independence sub-types** ($i_1, i_2, i_3, i_4$ on 0–5): {{ life_state.V.i1 }}, {{ life_state.V.i2 }}, {{ life_state.V.i3 }}, {{ life_state.V.i4 }}

## What we looked up

```
{{ research_json }}
```

## Paths scored, grouped by bucket

The buckets group paths that share the same overall stance. Each path is a sequence of stages over a {{ horizon_months }}-month horizon. We compute per-stage Momentum, sum duration-weighted, and tag each decision with a recoverability score $R(s_j) \in [0,1]$.

{% for bucket_name, label in [("bold_change", "Bold Change"), ("compounding_change", "Compounding Change"), ("creative_reinvention", "Creative Reinvention")] %}
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

Two short paragraphs. Acknowledge what they have already built first (career capital, savings, partnership, kids raised, recoveries already won). Then name the real tradeoff in plain language. If $\eta$ is negative, name that — it is signal, not a flaw. If $\nu$ is thin, acknowledge how that constrains plans that would isolate them further. If they said `ready_for_change` is high and `biggest_block` is something concrete (fear, money, time, family, identity), name the block by name. No bullet lists.

### What we looked up

Tight bullet list of the 3–5 most relevant numbers from the research. Each with a quick "what this means for you" tag. Cite sources as `[1]`, `[2]` inline; URLs go at the bottom.

### Three paths to consider

Render exactly three subsections — one per bucket — using `####` headings. **Treat them as equally legitimate framings.** From each bucket pick the strongest path (highest path momentum among viable+terminal-desirable; if none qualify, pick the highest-momentum viable; if still none, the highest-momentum and say why it doesn't pencil yet).

#### Bold Change Path

- **What this path is:** one sentence naming the chosen path and its first stage.
- **What it gives sooner:** 2–3 specific things in their language ($i_4$, $\eta$ lift, $g$ progress, etc.).
- **What it costs:** 2–3 specific costs (income gap, savings hit, household disruption, identity reset).
- **Recoverability of the load-bearing decision:** high | medium | low — one sentence on what could be undone if this turns out wrong.
- **Main risks:** 2–3 concrete risks tied to the per-stage math (which stage fails which floor).
- **First step this week if they choose this:** a single action, real and small.

#### Compounding Change Path

(Same structure.)

#### Creative Reinvention Path

(Same structure.)

### Our current best conjecture

**One paragraph.** Name which path the math currently favors. Open with: *"Given what you've told us, this seems strongest right now."* Connect the recommendation to their **top value**, the path-momentum ranking, and which viable/desirability filter the alternatives failed. If their `ready_for_change` is high and the math points at Bold Change, do not soften it into a compounding path. If it points at compounding, do not pretend a bold change is more recoverable than it is. End by naming the specific path and its first stage.

**If the recommendation involves training, school, or a credential**, name a specific program from the research bundle that fits **{{ answers.get("interests") | default("their stated interests") }}**, and say in one sentence why it fits. **If the recommendation involves starting a business**, ground it in the `business_landscape` numbers and {{ answers.get("business_idea") | default("the idea they shared") }}. **If the recommendation involves a move**, ground it in the `relocation` numbers for {{ answers.get("move_destination") | default("the destination they named") }}.

If `wants_education` is empty or only contains `no_formal_training`, do not push training as the recommendation.

### Key assumptions this depends on

4–6 short bullets. The assumptions baked into the recommendation. Examples: *"Your partner is on board with the timeline."*, *"You can hold $X/mo in expenses through the runway."*, *"Childcare coverage stays roughly stable."*, *"You complete the program — $\rho$ for someone with your time situation is roughly 30%, meaning a 70% chance of completion."*, *"$\delta$ for the destination field is non-negative over a 5-year horizon."*

### What could break this plan

3–5 short bullets. Conditions that would weaken the recommendation. Examples: *"Your hours at the day job get cut."*, *"$\eta$ at home drops further."*, *"A health event surfaces that you've been deferring."*, *"The business doesn't reach the revenue milestone in the runway window."*, *"A parent's care needs accelerate."*

### What would change our mind

3–5 short bullets. Specific evidence that would shift toward a different bucket. Examples: *"If a part-time consulting offer at $X/mo materializes, Compounding Change moves up."*, *"If the program you researched offers a deferred-start option, Creative Reinvention strengthens."*, *"If $\eta$ stays negative for another six months, Bold Change moves up regardless of cash flow."*

### Revisit this in

One concrete trigger or window. Examples: *"60 days, after you've sat with one program's open-house and one informational interview."* / *"90 days, after the first quarter on the new schedule."* / *"30 days, after you and your partner have had the conversation."* Pick a real trigger, not a vague time.

### What to watch for

3–5 short bullets of the fragility risks specific to the recommended path. *"If sleep degrades below X for two weeks…"*, *"If buffer hours go to zero, the practice will be the first to drop…"*, *"If the runway burn rate exceeds $X/mo, shorten the runway not the savings…"*, *"If the partnership conversation keeps not happening, the plan is not actually proceeding."* This is where the wisdom shows.

### Sources

Numbered list of URLs from the research bundle.

---

Length: aim for **900–1200 words**. If it's longer, you're lecturing.
