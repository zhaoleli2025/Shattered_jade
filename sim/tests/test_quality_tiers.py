"""品阶 quality grades: quality buys numbers, family buys verbs."""
import copy

import pytest

from sim import data
from sim.state import grade_armor, grade_weapon, load_scenario, make_unit

LADDER = [data.QUALITY[k] for k in ("fan", "liang", "jing", "zhen", "shen")]


def test_ladder_monotonicity():
    assert [g["rank"] for g in LADDER] == [0, 1, 2, 3, 4]
    for lo, hi in zip(LADDER, LADDER[1:]):
        assert hi["dmg"] > lo["dmg"]
        assert hi["acc"] > lo["acc"]
        assert hi["protect"] > lo["protect"]
        assert hi["br_tax"] <= lo["br_tax"]  # finer work never drags more


def test_fan_is_identity():
    wpn = grade_weapon(copy.deepcopy(data.WEAPONS["yaodao"]), data.QUALITY["fan"])
    base = data.WEAPONS["yaodao"]
    assert (wpn["dmin"], wpn["dmax"], wpn["acc"], wpn["br_tax"], wpn["label"]) == \
        (base["dmin"], base["dmax"], base["acc"], base["br_tax"], base["label"])
    body = grade_armor(data.ARMOR["tiejia"], data.QUALITY["fan"])
    assert (body["protect"], body["br_tax"], body["label"]) == (110, 16, "铁甲")


def test_exact_application_math():
    wpn = grade_weapon(copy.deepcopy(data.WEAPONS["yaodao"]), data.QUALITY["jing"])
    assert (wpn["dmin"], wpn["dmax"], wpn["acc"], wpn["label"]) == \
        (22, 31, 14, "精品·腰刀")
    assert wpn["br_tax"] == 2  # q_round(2 × 0.95) — the tax barely budges
    body = grade_armor(data.ARMOR["tiejia"], data.QUALITY["shen"])
    assert (body["protect"], body["br_tax"], body["label"]) == (193, 14, "神品·铁甲")
    assert data.WEAPONS["yaodao"]["dmin"] == 18  # base table never mutated
    assert data.ARMOR["tiejia"]["protect"] == 110


def test_roster_defaults():
    s = load_scenario("jiebiao")
    liu = s.by_id("liu").wpn   # 精品·腰刀 main
    assert (liu["dmin"], liu["dmax"], liu["acc"], liu["quality"]) == (22, 31, 14, "jing")
    yan = s.by_id("yan").wpn   # 良品·猎弓
    assert (yan["dmin"], yan["dmax"], yan["acc"]) == (15, 26, 12)


def test_weapon_br_tax_in_breath_max():
    s = load_scenario("jiebiao")
    wang = s.by_id("wang")     # both weapons taxed: 87 − 8 − 3 − 4(枪) − 2(刀)
    assert wang.breath_max == 70
    lu = load_scenario("gongzhai").by_id("lu")  # 89 − 8 − 1 − 4(弩) − 1(短刀)
    assert lu.breath_max == 75  # the sheathed sidearm still drags


def test_scenario_override():
    s = load_scenario("duijue")
    diao = s.by_id("diao")     # showcase: 良品 armor only (v0.23 ladder re-tune)
    assert (diao.armor_b, diao.armor_h) == (127, 80)
    assert (diao.wpn["dmin"], diao.wpn["dmax"], diao.wpn["acc"]) == (24, 34, 10)
    assert diao.armor_name == "良品·铁甲"
    assert diao.breath_max == 65  # 良品 br_tax ×1.00 — no extra 坠气 relief


def test_unknown_quality_raises():
    tpl = dict(next(t for t in data.ROSTER if t["id"] == "liu"), wpn_q="xianpin")
    with pytest.raises(ValueError, match="xianpin.*fan.*liang.*jing.*zhen.*shen"):
        make_unit(tpl, 0, 0)
    tpl = next(t for t in data.ROSTER if t["id"] == "diao")
    with pytest.raises(ValueError, match="xianpin"):
        make_unit(tpl, 0, 0, overrides={"armor_q": "xianpin"})


def test_falsy_override_fails_loud():
    """A PRESENT key with value "" must raise, never silently fall back;
    only an absent key (or null) walks scenario → template → 凡品."""
    tpl = next(t for t in data.ROSTER if t["id"] == "liu")
    with pytest.raises(ValueError, match="''"):
        make_unit(tpl, 0, 0, overrides={"wpn_q": ""})
    # eager across all four slots: liu carries no wpn2, the check still fires
    with pytest.raises(ValueError, match="''"):
        make_unit(tpl, 0, 0, overrides={"wpn2_q": ""})
