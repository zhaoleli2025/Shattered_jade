"""Armor tier system: protection vs weight, computed loadouts."""
from sim import data
from sim.state import load_scenario


def test_tier_ordering():
    body = [data.ARMOR[k] for k in ("bujia", "pijia", "tiejia")]
    head = [data.ARMOR[k] for k in ("bumao", "pikui", "tiekui")]
    for seq in (body, head):
        for lighter, heavier in zip(seq, seq[1:]):
            assert heavier["protect"] > lighter["protect"]
            assert heavier["weight"] > lighter["weight"]  # protection costs Breath


def test_roster_loadouts_valid():
    for tpl in data.ROSTER:
        assert data.ARMOR[tpl["armor"]]["slot"] == "body"
        assert data.ARMOR[tpl["helmet"]]["slot"] == "head"
        assert tpl["breath_base"] > data.ARMOR[tpl["armor"]]["weight"] + \
            data.ARMOR[tpl["helmet"]]["weight"]


def test_weight_taxes_breath():
    s = load_scenario("jiebiao")
    shi = s.by_id("shi")      # iron + iron: 93 − 16 − 7
    assert (shi.breath_max, shi.armor_b, shi.armor_h) == (70, 110, 80)
    assert (shi.armor_name, shi.helm_name) == ("铁甲", "铁盔")
    yan = s.by_id("yan")      # cloth + cap: 94 − 3 − 1
    assert (yan.breath_max, yan.armor_b, yan.armor_h) == (90, 25, 15)
    # the iron man starts the battle 20 Breath poorer than the runner
    assert yan.breath_max - shi.breath_max == 20
