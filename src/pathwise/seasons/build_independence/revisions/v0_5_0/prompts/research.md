# Research brief

You're researching real-world numbers so the plan we generate for **{{ profile.first_name }}** is grounded, not generic.

## What we know about them

- First name: **{{ profile.first_name }}**
- Location: {% if profile.zip_code %}**ZIP {{ profile.zip_code }}**{% else %}*not provided — use US national figures and say so*{% endif %}
- Currently {% if answers.lives_with_parents %}lives with family{% else %}lives independently{% endif %}, {% if answers.has_car %}has a car{% else %}no car{% endif %}.
- Savings: roughly **${{ answers.current_savings | default(0) }}**.
- Debt: **${{ answers.current_debt | default(0) }}**.
- Take-home income: **${{ answers.current_monthly_take_home | default(0) }}/mo**.
- Monthly bills (excluding rent): **${{ answers.current_monthly_bills | default(0) }}/mo**.
- Stated interests: {{ answers.interests | default("(none provided)") }}.
- Wants on the table:
{%- for cat in ["wants_mobility","wants_housing","wants_education","wants_work","wants_relationships","wants_place","wants_health","wants_money_goals","wants_lifestyle"] %}
  - **{{ cat }}**: {{ answers.get(cat) | default("[]") }}
{%- endfor %}

## Use the web_search tool to find

Match research to the user's wants. Don't research what they're not considering.

1. **If `wants_mobility` includes `car`**: used car market in their area (or US national if no ZIP). For each tier (reliable basic transportation ~10 yrs old, and modest but newer ~5 yrs old): typical price band, plus typical full-coverage insurance for an 18-year-old.
2. **If `wants_housing` includes `move_out`**: local rent for a 1-bedroom and a room-in-a-shared-house. Median + low end.
3. **If `wants_education` has anything other than `no_formal_training`**: top 2–3 skill paths that match their interests **or** that have strong wage growth in their area. For each:
   - Name and where you'd actually take it (community college / trade school / online / 4-year)
   - Typical tuition / total cost
   - Typical time-to-completion
   - Typical entry-level wage on completion (local if possible)
   - **Technology trajectory ($\delta$)**: brief note on whether the field is exposed to displacement, neutral, or amplified by emerging technology over the next 5 years.
4. **Local minimum wage and prevailing wages** for entry-level jobs in their area, so we can sanity-check the income side. Always include this.

## Output format

Return a single JSON object with this shape (no prose, no markdown):

```json
{
  "location_used": "ZIP 30301" | "US national average",
  "used_car": {
    "basic_tier": { "price_low": 0, "price_high": 0, "examples": [], "notes": "" },
    "modest_tier": { "price_low": 0, "price_high": 0, "examples": [], "notes": "" },
    "insurance_18yo_monthly_low": 0,
    "insurance_18yo_monthly_high": 0
  },
  "rent": {
    "room_in_shared_house_monthly_low": 0,
    "room_in_shared_house_monthly_high": 0,
    "one_bedroom_monthly_low": 0,
    "one_bedroom_monthly_high": 0
  },
  "skill_paths": [
    {
      "name": "",
      "delivered_by": "",
      "tuition_total": 0,
      "months_to_complete": 0,
      "entry_wage_monthly_low": 0,
      "entry_wage_monthly_high": 0,
      "fits_interest": "",
      "technology_trajectory": ""
    }
  ],
  "wages": {
    "minimum_hourly": 0,
    "common_entry_hourly_low": 0,
    "common_entry_hourly_high": 0
  },
  "sources": ["url1", "url2", "..."]
}
```

If a section isn't relevant to this user's wants, omit it from the output (or set to `null`). If you genuinely cannot find a number after searching, use `null` and add a one-line `"notes"` explaining. Don't invent.
