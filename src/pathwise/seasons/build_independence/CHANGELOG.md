# Build Independence — Revision History

## 0.5.0

Major model revision. The conjecture was rewritten from the ground up
(see `revisions/v0_5_0/model.md`):

- New life-state shape `L = {V, T, A, K, W}`. Income absorbed into `A`.
  `K` reshaped from "skills" into "education" with five sub-components.
  `W` (health) is new, with five sub-components including emotional
  impact and relational quality.
- Two-tier filtering: `L_viable` (survival) vs. `L_desirable`
  (worth-wanting). Single-scenario optimum picks from desirable.
- Path-level scoring: paths are sequences of stages with durations
  bounded by horizon `H`. Momentum sums duration-weighted life-state
  quality across stages.
- Per-decision recoverability `R(s_j)` computed from lock-in / exit
  cost / state disruption — replaces the static per-scenario field.
- New weights table (§3.5). `q · e` cross-term operationalizes
  "time directed at enjoyment."
- Questionnaire: 9-category multi-select wants section drives
  conditional state-collection questions.

## 0.4.0

Schema revision (no question content changes). The questionnaire now lives in
`questionnaire.json` instead of `questions.yaml`, with three explicit
sections: `data_model` (durable contract with the deterministic core),
`questions` (UI presentation per field), and `steps` (ordered groups for the
wizard). Conditional `when` predicates hide steps and questions based on
prior answers (e.g. car questions only appear when needed). All answer keys
preserved from 0.3.0.

## 0.3.0

Initial published revision after sweeping edits to the underlying conjecture
(see `model.md`):

- A-rename (asset terminology)
- H as a modulator (home-emotional cost folded into momentum)
- Three-paths plan output (no ladder default)
- Per-decision recoverability separated from life-state fragility
