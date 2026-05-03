# Build Independence — Revision History

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
