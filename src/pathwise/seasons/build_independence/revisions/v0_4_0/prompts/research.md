# Research brief

You're researching real-world numbers so the plan we generate for **{{ profile.first_name }}** is grounded, not generic.

## What we know about them

- First name: **{{ profile.first_name }}**
- Location: {% if profile.zip_code %}**ZIP {{ profile.zip_code }}**{% else %}*not provided — use US national figures and say so*{% endif %}
- Currently {% if answers.lives_with_parents %}lives with family{% else %}lives independently{% endif %}, {% if answers.has_car %}has a car{% else %}no car{% endif %}.
- Savings: roughly **${{ answers.current_savings | default(0) }}**.
- Take-home income: **${{ answers.current_monthly_take_home | default(0) }}/mo**.
- Monthly bills (excluding rent): **${{ answers.current_monthly_bills | default(0) }}/mo**.
- Open to training: **{{ "yes" if answers.interested_in_training else "no" }}**{% if answers.training_modality %} (preferred modality: {{ answers.training_modality }}){% endif %}.
- Stated interests: {{ answers.interests | default("(none provided)") }}.

## Use the web_search tool to find

1. **Used car market** in their area (or US national if no ZIP). For each of:
   - "reliable basic transportation" tier (e.g. used Civic / Corolla / Sentra, ~10 yrs old, <120k miles)
   - "modest but newer" tier (~5 yrs old)
   Report a typical price band, plus typical full-coverage insurance for an 18-year-old in that area.
2. **Local rent** for a 1-bedroom and a room-in-a-shared-house, in their area. Median + low end.
3. **Top 2–3 skill paths** that match their interests **or** that have strong wage growth in their area. For each:
   - Name and where you'd actually take it (community college / trade school / online)
   - Typical tuition / total cost
   - Typical time-to-completion
   - Typical entry-level wage on completion (local if possible)
4. **Local minimum wage and prevailing wages** for entry-level jobs in their area, so we can sanity-check the income side.

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
      "fits_interest": ""
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

If you genuinely cannot find a number after searching, use `null` for that field and add a one-line `"notes"` explaining. Don't invent.
