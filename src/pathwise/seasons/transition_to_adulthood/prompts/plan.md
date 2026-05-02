# Synthesize {{ profile.first_name }}'s plan

You have everything needed. Write a calm, specific, digestible plan for **{{ profile.first_name }}**, in the voice and constraints from the system prompt. Plans are conjectures, not verdicts — three paths are equally legitimate framings; the recommended one is the path the math currently favors and is open to revision.

## What they told us

{% for q in questions %}{% if answers.get(q.key) not in (None, "", []) -%}
- **{{ q.prompt }}** {{ format_answer(q, answers[q.key]) }}
{% endif %}{% endfor %}

## What we computed (deterministic)

- Current monthly cash flow estimate: **${{ life_state.cash_flow_monthly }}/mo**
- Current emergency buffer relative to their floor: **{{ life_state.buffer_status }}**
- Productive time band: **{{ life_state.productive_time_band }}**
- Stated top value: **{{ life_state.top_value }}**
- Stay-home emotional cost (H for the stay-home scenarios): **{{ life_state.home_emotional_label }}** ({% if not life_state.lives_with_parents %}lives independently{% else %}lives with family{% endif %})

## What we looked up

```
{{ research_json }}
```

## Scenarios scored, grouped by path bucket

The three named buckets group scenarios that share the same overall stance. Each scenario carries its own recoverability tag (high / medium / low) — how easily {{ profile.first_name }} can step back if the choice turns out wrong.

{% for bucket_name, label in [("fast_freedom", "Fast Freedom"), ("compounding_freedom", "Compounding Freedom"), ("skill_leverage", "Skill-Leverage")] %}
**{{ label }} bucket:**
{% for s in paths_by_bucket.get(bucket_name, []) %}
- {{ s.label }} — momentum {{ "%.2f"|format(s.momentum) }}, viable: {{ s.viable }}{% if not s.viable %} (fails: {{ s.fails | join(", ") }}){% endif %}, recoverability: {{ s.recoverability }}.
  Estimated impact: cash flow {{ s.cash_flow_delta_str }}/mo, buffer {{ s.buffer_delta_str }}, productive time {{ s.time_delta_str }}.
{% else %}
- (no scenarios in this bucket)
{% endfor %}

{% endfor %}
{% if chat_context %}
## Conversation since the last plan

{{ profile.first_name }} talked through the previous plan with you. Use what they said to update the new plan. Where the conversation revealed new information about their situation, change the math. Where it revealed a different priority or a misunderstanding, name that explicitly and adjust accordingly. Don't ignore what they pushed back on.

{{ chat_context }}

{% endif %}
## Write the plan

Use this exact structure (markdown headings). Three paths get equal real estate; the recommended one is named separately afterward.

### Where you are now

Two short paragraphs. Acknowledge their current strengths first (savings, the job they have, the values they ranked, what they've already built). Then name the real tradeoff they're facing in plain language. If their home emotional cost is `tense` or `hard`, acknowledge that staying home isn't free here. No bullet lists.

### What we looked up

Tight bullet list of the 3–5 most relevant numbers from the research. Each with a quick "what this means for you" tag. Cite sources as `[1]`, `[2]` inline; URLs go at the bottom.

### Three paths to consider

Render exactly three subsections — one per bucket — using `####` headings. **Treat them as equally legitimate framings.** Pick the strongest scenario from each bucket (highest momentum among viable ones; if none viable in that bucket, pick the highest-momentum non-viable and say why it doesn't pencil right now).

#### Fast Freedom Path

- **What this path is:** one sentence naming the chosen scenario.
- **What it gives you sooner:** 2–3 specific things ({{ profile.first_name }}'s residential independence, decision independence, etc.).
- **What it delays:** 2–3 specific things (savings rate, car upgrade, training, etc.).
- **Recoverability:** {high | medium | low} — one sentence explaining what could be undone if this turns out wrong.
- **Main risks:** 2–3 concrete risks tied to the math we computed.
- **First step this week if you choose this:** a single action, real and small.

#### Compounding Freedom Path

(Same structure as above.)

#### Skill-Leverage Path

(Same structure as above.)

### Our current best conjecture

**One paragraph.** Name which path the math currently favors. Open with the framing: *"Given what you've told us, this seems strongest right now."* Then explain *why* in plain language — connect it to their stated top value, their cash flow / buffer / productive time, and their emotional cost (what staying or moving or training would emotionally pay). Do not lean on a prescribed "build mobility/financial first" ordering — the model treats the independence ladder as multi-dimensional, not sequential. End by naming the specific scenario inside the favored bucket.

**If the recommendation involves training, school, or a certificate**, you must name a specific program from the research bundle's `skill_paths` that fits **{{ answers.interests | default("their stated interests") }}**, and say in one sentence why it fits. If none of the researched paths fit their interests, say so honestly — don't recommend a path that contradicts what they told us. If they marked themselves not open to training (`interested_in_training` = no), do not push training as the recommendation.

### Key assumptions this depends on

4–6 short bullets. The assumptions baked into the recommendation. Examples: *"You can keep working ~25 hrs/wk."*, *"Insurance falls in the $X–$Y range we found."*, *"You want to keep at least $X in savings."*, *"You're willing to delay moving out 6–12 months."*

### What could break this plan

3–5 short bullets. Conditions under the recommendation that would weaken it. Examples: *"Your work hours get cut."*, *"Insurance comes back above $X."*, *"Home becomes emotionally unhealthy."*, *"You lose motivation for the training path."*

### What would change our mind

3–5 short bullets. Specific evidence that would shift us toward a different path. Examples: *"If a stable roommate offer at $X/mo comes up, Fast Freedom moves up the list."*, *"If you can hold $X/mo in savings while training, Skill-Leverage strengthens."* If their home emotional cost is `tense` or `hard`, explicitly include the condition that would make moving out sooner the right call.

### Revisit this in

One concrete trigger or window. Examples: *"30 days, after you have insurance quotes in hand."* / *"60 days, once you've tracked actual hours and spending."* / *"90 days, after you've tested whether the work + training schedule is sustainable."* Pick a real trigger, not a vague time.

### What to watch for

3–5 short bullets of the fragility risks specific to the recommended path. *"If your hours drop below X…"*, *"If a $1k repair hits…"*, *"If rent climbs above X% of take-home…"*. This is where the wisdom shows.

### Sources

Numbered list of URLs from the research bundle.

---

Length: aim for **800–1100 words**. If it's longer, you're lecturing.
