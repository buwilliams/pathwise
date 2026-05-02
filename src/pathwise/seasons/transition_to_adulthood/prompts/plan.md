# Synthesize {{ profile.first_name }}'s plan

You have everything needed. Write a calm, specific, digestible plan for **{{ profile.first_name }}**, in the voice and constraints from the system prompt.

## What they told us

{% for q in questions %}{% if answers.get(q.key) not in (None, "", []) -%}
- **{{ q.prompt }}** {{ format_answer(q, answers[q.key]) }}
{% endif %}{% endfor %}

## What we computed (deterministic)

- Current monthly cash flow estimate: **${{ life_state.cash_flow_monthly }}/mo**
- Current emergency buffer relative to their floor: **{{ life_state.buffer_status }}**
- Productive time band: **{{ life_state.productive_time_band }}**
- Stated top value: **{{ life_state.top_value }}**

## What we looked up

```
{{ research_json }}
```

## Scenarios scored (highest momentum first)

{% for s in scored_scenarios %}
**{{ loop.index }}. {{ s.label }}** — momentum {{ "%.2f"|format(s.momentum) }}, viable: {{ s.viable }}{% if not s.viable %} (fails: {{ s.fails | join(", ") }}){% endif %}
{{ s.description }}
Estimated impact: cash flow {{ s.cash_flow_delta_str }}/mo, buffer {{ s.buffer_delta_str }}, productive time {{ s.time_delta_str }}.

{% endfor %}

## Write the plan

Use this exact structure (markdown headings):

### Where you are now

Two short paragraphs. Acknowledge their current strengths first (savings, the
job they have, the values they ranked). Then name the real tradeoff they're
facing in plain language. No bullet lists here.

### What we looked up

Tight bullet list of the 3–5 most relevant numbers from the research. Each
with a quick "what this means for you" tag. Cite sources as `[1]`, `[2]`
inline; the source URLs go at the bottom.

### Paths we considered

For the top 3 scenarios by momentum: a short paragraph each. Name the path,
say what it's good at, say what its risk is. Be honest about the rejected
ones — don't pretend they're equal.

### Recommended path

One paragraph. Name the path. Say *why* — connect it back to what they told
us they value and what the numbers say is viable. Name the independence-ladder
logic if it applies.

### The next small step

A single concrete action they could take **this week** to start. Not the
whole mountain — the next small move. Examples: "Pull a free credit report",
"Open a HYSA and move $X into it", "Visit one shop / one program",
"Track every dollar for two weeks". Make it real and small.

### What to watch for

3–5 short bullets of the fragility risks specific to this plan. "If your
hours drop below X…", "If a $1k repair hits…", "If rent climbs above X% of
take-home…". This is where the wisdom shows.

### Sources

Numbered list of URLs from the research bundle.

---

Length: aim for **600–900 words**. If it's longer, you're lecturing.
