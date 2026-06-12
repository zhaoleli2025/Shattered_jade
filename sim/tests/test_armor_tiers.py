"""Armor tier system: protection vs 坠气 (the carry tax), computed loadouts."""
from sim import data
from sim.state import load_scenario, make_unit


def test_tier_ordering():
    body = [data.ARMOR[k] for k in ("bujia", "pijia", "tiejia")]
    head = [data.ARMOR[k] for k in ("bumao", "pikui", "tiekui")]
    for seq in (body, head):
        for lighter, heavier in zip(seq, seq[1:]):
            assert heavier["protect"] > lighter["protect"]
            assert heavier["br_tax"] > lighter["br_tax"]  # protection costs Breath


def test_roster_loadouts_valid():
    for tpl in data.ROSTER:
        assert data.ARMOR[tpl["armor"]]["slot"] == "body"
        assert data.ARMOR[tpl["helmet"]]["slot"] == "head"
        # full 坠气 load (armor+helm+weapons) leaves every man real wind
        assert make_unit(tpl, 0, 0).breath_max > 40


def test_br_tax_drains_breath_max():
    s = load_scenario("jiebiao")
    shi = s.by_id("shi")      # iron + iron + hammer: 93 − 16 − 7 − 6
    assert (shi.breath_max, shi.armor_b, shi.armor_h) == (64, 110, 80)
    assert (shi.armor_name, shi.helm_name) == ("铁甲", "铁盔")
    yan = s.by_id("yan")      # cloth + cap + bow + dagger: 94 − 3 − 1 − 2 − 1
    assert (yan.breath_max, yan.armor_b, yan.armor_h) == (87, 25, 15)
    # the iron man starts the battle 23 Breath poorer than the runner
    assert yan.breath_max - shi.breath_max == 23
