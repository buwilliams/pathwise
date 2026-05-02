from __future__ import annotations

from pathwise.core.season import get_pack, list_packs, packs_root


def test_default_pack_loads() -> None:
    pack = get_pack("transition-to-adulthood")
    assert pack.id == "transition-to-adulthood"
    assert pack.name
    assert pack.summary
    assert pack.questions
    assert pack.scenarios
    assert pack.weights["c"] == 4  # cash flow weight from the model
    assert pack.weights["s"] == 4  # stability weight


def test_questions_have_required_fields() -> None:
    pack = get_pack("transition-to-adulthood")
    keys = pack.question_keys()
    assert len(keys) == len(set(keys)), "duplicate question keys"
    for q in pack.questions:
        assert q.key
        assert q.prompt
        assert q.section
        if q.type in ("single_choice", "multi_choice"):
            assert q.options, f"{q.key} needs options"


def test_scenarios_match_model() -> None:
    pack = get_pack("transition-to-adulthood")
    ids = {s.id for s in pack.scenarios}
    # The 7 scenarios from emma-life-strategy-model.md §Candidate Scenarios
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
    pack = get_pack("transition-to-adulthood")
    for name in ("system", "research", "plan"):
        assert pack.prompt_path(name).exists(), f"missing prompts/{name}.md"


def test_list_packs_finds_default() -> None:
    packs = list_packs(packs_root())
    ids = {p.id for p in packs}
    assert "transition-to-adulthood" in ids
