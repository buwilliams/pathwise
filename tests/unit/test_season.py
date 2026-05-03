from __future__ import annotations

import pytest

from pathwise.core.season import (
    get_pack,
    latest_revision,
    list_packs,
    list_revisions,
)


def test_default_pack_loads() -> None:
    pack = get_pack("build-independence")
    assert pack.id == "build-independence"
    assert pack.name
    assert pack.summary
    assert pack.questionnaire.questions
    assert pack.scenarios
    assert pack.weights["c"] == 4  # cash flow weight from the model
    assert pack.weights["s"] == 4  # stability weight


def test_questions_have_required_fields() -> None:
    pack = get_pack("build-independence")
    qn = pack.questionnaire
    keys = list(qn.questions)
    assert len(keys) == len(set(keys)), "duplicate question keys"
    for qkey, q in qn.questions.items():
        assert q.prompt
        # Every question must have a matching data_model entry — schema enforces this.
        assert qkey in qn.data_model
        if q.input.kind in ("single_choice", "multi_choice"):
            assert q.input.options, f"{qkey} needs options"


def test_scenarios_match_model() -> None:
    pack = get_pack("build-independence")
    ids = {s.id for s in pack.scenarios}
    # The 7 scenarios from model.md §Candidate Scenarios
    expected = {
        "stay_no_car_save",
        "stay_modest_car",
        "move_out_with_car",
        "move_out_no_car",
        "low_rent_modest_car_grow_income",
        "work_more_save_more",
        "train_for_better_income",
    }
    assert ids == expected


def test_prompts_exist() -> None:
    pack = get_pack("build-independence")
    for name in ("system", "research", "plan"):
        assert pack.prompt_path(name).exists(), f"missing prompts/{name}.md"


def test_list_packs_finds_default() -> None:
    packs = list_packs()
    ids = {p.id for p in packs}
    assert "build-independence" in ids


def test_revision_api() -> None:
    revs = list_revisions("build-independence")
    assert "0.4.0" in revs
    assert latest_revision("build-independence") == "0.4.0"
    pack = get_pack("build-independence", revision="0.4.0")
    assert pack.revision == "0.4.0"
    assert pack.version == "0.4.0"


def test_unknown_revision_raises() -> None:
    with pytest.raises(KeyError):
        get_pack("build-independence", revision="9.9.9")


def test_unknown_season_raises() -> None:
    with pytest.raises(KeyError):
        get_pack("nonexistent-season")
