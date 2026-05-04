# Research brief

You're researching real-world numbers so the plan we generate for **{{ profile.first_name }}** is grounded, not generic.

## What we know about them

- First name: **{{ profile.first_name }}**
- Location: {% if profile.zip_code %}**ZIP {{ profile.zip_code }}**{% else %}*not provided — use US national figures and say so*{% endif %}
- Relationship: {{ answers.relationship_status | default("not provided") }}
- Caregiving: {{ answers.has_dependents | default("not provided") }}
- Liquid savings: **${{ answers.current_savings | default(0) }}**
- Retirement: **${{ answers.retirement_savings | default(0) }}**
- Debt (non-mortgage): **${{ answers.current_debt | default(0) }}**
- Household take-home: **${{ answers.current_monthly_take_home | default(0) }}/mo**
- Household bills: **${{ answers.current_monthly_bills | default(0) }}/mo**
- Career feeling: {{ answers.career_feeling | default("not provided") }}
- Stated interests: {{ answers.interests | default("(none provided)") }}
- Wants on the table:
{%- for cat in ["wants_career","wants_education","wants_relationships","wants_family","wants_place","wants_health","wants_money_goals","wants_creative","wants_lifestyle"] %}
  - **{{ cat }}**: {{ answers.get(cat) | default("[]") }}
{%- endfor %}
{%- if answers.business_idea %}
- Business idea: {{ answers.business_idea }}
{%- endif %}
{%- if answers.move_destination %}
- Considering moving to: {{ answers.move_destination }}
{%- endif %}

## Use the web_search tool to find

Match research to the user's wants. Don't research what they're not considering.

1. **If `wants_career` includes `pivot_field` or `change_role`**: 2–3 destination roles or fields that fit their stated interests, with current US (or local) entry-level and mid-level pay bands. For each, note a typical mid-career-pivot transition path (relevant credentials or work-sample requirements).

2. **If `wants_career` includes `start_business`** and a `business_idea` was provided: realistic startup costs, typical time-to-revenue, and 2–3 example businesses in that space with publicly known revenue or scale. Honest numbers, including failure rates.

3. **If `wants_education` has anything other than `no_formal_training`**: 2–3 specific programs that fit their interests **and** their `education_modality` preference. For each:
   - Name and provider
   - Typical tuition / total cost (including any common employer-reimbursement patterns)
   - Typical time-to-completion
   - Typical post-completion wage or career impact for someone changing fields at midlife
   - **Technology trajectory ($\delta$)**: brief note on whether the field is exposed to displacement, neutral, or amplified by emerging technology over the next 5–10 years.

4. **If `wants_place` includes `move_city` or `move_country`** and a destination was provided: cost-of-living comparison vs. their current ZIP (housing, taxes, healthcare). Median home/rent prices. Note one or two real considerations specific to that destination (climate, school quality, visa for international, healthcare).

5. **If `wants_health` includes `mental_health_support` or `recovery_from_burnout`**: 1–2 recognized evidence-based options (therapy modalities, intensive programs, sabbatical structures), typical cost, and access notes. Do not diagnose. Do not recommend specific clinicians.

6. **If `wants_money_goals` includes `pay_down_debt` or `retirement_boost`**: current rules-of-thumb that apply to their situation (e.g. catch-up contribution limits if 50+ is on the horizon, current refinancing rates, debt-snowball vs. avalanche math at typical interest rates).

7. **Median household income and prevailing wages** in their area for their current occupation. Always include this as a sanity check.

## Output format

Return a single JSON object with this shape (no prose, no markdown):

```json
{
  "location_used": "ZIP 30301" | "US national average",
  "career_paths": [
    {
      "name": "",
      "fits_interest": "",
      "entry_wage_monthly_low": 0,
      "entry_wage_monthly_high": 0,
      "mid_wage_monthly_low": 0,
      "mid_wage_monthly_high": 0,
      "transition_path": "",
      "technology_trajectory": ""
    }
  ],
  "business_landscape": {
    "startup_cost_low": 0,
    "startup_cost_high": 0,
    "months_to_first_revenue_typical": 0,
    "months_to_break_even_typical": 0,
    "examples": [{ "name": "", "scale": "" }],
    "failure_rate_notes": ""
  },
  "education_paths": [
    {
      "name": "",
      "provider": "",
      "tuition_total": 0,
      "months_to_complete": 0,
      "post_completion_wage_monthly_low": 0,
      "post_completion_wage_monthly_high": 0,
      "fits_interest": "",
      "technology_trajectory": ""
    }
  ],
  "relocation": {
    "destination": "",
    "median_home_price": 0,
    "median_rent_1br": 0,
    "cost_of_living_index_vs_current": 0,
    "tax_notes": "",
    "specific_considerations": ""
  },
  "health_options": [
    {
      "name": "",
      "modality": "",
      "typical_cost_monthly": 0,
      "access_notes": ""
    }
  ],
  "money_rules_of_thumb": {
    "retirement_catch_up_age": 50,
    "current_30yr_mortgage_rate": null,
    "debt_strategy_notes": ""
  },
  "wages_local": {
    "median_household_monthly": 0,
    "current_occupation_median_monthly": 0
  },
  "sources": ["url1", "url2", "..."]
}
```

If a section isn't relevant to this user's wants, omit it from the output (or set to `null`). If you genuinely cannot find a number after searching, use `null` and add a one-line `"notes"` explaining. Don't invent.
