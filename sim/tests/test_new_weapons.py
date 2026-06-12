"""攻寨 arsenal: flail (shield-ignore, head-hunting), crossbow, 1H spearwall, walls."""
from sim.ai import ai_turn
from sim.commands import Stance, can_special, resolve
from sim.engine import run_battle
from sim.pathfind import dijkstra
from sim.rules import apply_hit, compute_damage, hit_breakdown, special_opts
from sim.state import load_scenario
from sim import data
from sim.tests.test_subsystems import FakeRNG, move_to, park_others, ready


def S(seed=0):
    return load_scenario("gongzhai", seed)


def test_flail_ignores_shield_but_not_shieldwall_extra():
    s = S()
    flail = move_to(s, "he", 6, 5)
    diao = move_to(s, "diao", 6, 6)  # shield 15, dfn 12
    parts = dict(hit_breakdown(s, flail, diao)[0])
    assert parts["defense"] == -12          # shield's base 15 ignored
    diao.shieldwall = True
    parts = dict(hit_breakdown(s, flail, diao)[0])
    assert parts["defense"] == -27          # raised-shield extra still counts (BB)
    # control: a saber respects the full 12+15 (and 2× when raised)
    saber = move_to(s, "duyan", 5, 6)
    parts = dict(hit_breakdown(s, saber, diao)[0])
    assert parts["defense"] == -42


def test_flail_head_bonus_and_forced_head():
    s = S()
    flail = ready(move_to(s, "he", 6, 5))
    foe = move_to(s, "duyan", 6, 6)
    s.rng = FakeRNG([1, 30, 20])            # head roll 30: ≤ 25+10 → head for flail
    apply_hit(s, flail, foe)
    assert [e for e in s.events if e["type"] == "hit"][-1]["head"] is True
    foe.hp, foe.armor_h = 50, 50
    s.rng = FakeRNG([1, 99, 20])            # head roll 99 — only 兜头 forces it
    apply_hit(s, flail, foe, opts=special_opts(flail.wpn["special"]))
    e = [e for e in s.events if e["type"] == "hit"][-1]
    assert e["head"] is True and e["tag"] == "兜头"


def test_crossbow_profile():
    w = data.WEAPONS["nu"]
    armor_dmg, hp = compute_damage(27, 60, w, head=False)
    assert armor_dmg == 22                  # js_round(27 × 0.8)
    assert hp == 8                          # 27×0.5 − 6, strong pierce
    s = S()
    lu = ready(move_to(s, "lu", 0, 0))
    park_others(s, {"lu", "duyan"})
    move_to(s, "duyan", 7, 0)               # beyond range 6 → not a target
    from sim.commands import ranged_targets
    assert ranged_targets(s, lu) == []
    move_to(s, "duyan", 6, 0)
    assert [t.uid for t in ranged_targets(s, lu)] == ["duyan"]


def test_one_hand_spearwall_with_shield():
    s = S()
    chen = ready(move_to(s, "chen", 2, 2))
    assert resolve(s, chen, Stance("spearwall")) is True
    assert chen.spearwall and chen.shield == 15  # wall AND shield together
    assert resolve(s, chen, Stance("shieldwall")) is True  # both stances legal


def test_walls_block_pathing():
    s = S()
    unit = ready(move_to(s, "he", 8, 1))    # just north of the wall line
    park_others(s, {"he"})
    costs, _, _ = dijkstra(s, unit, 99, 999)
    for wk in [(7, 2), (8, 2), (9, 2), (9, 3), (8, 4), (7, 5), (5, 5)]:
        assert wk not in costs              # nobody stands on the village wall


def test_ai_spear_defender_sets_wall():
    s = S()
    park_others(s, {"shemao", "chen"}, where=(-4, 8))
    shemao = ready(move_to(s, "shemao", 6, 4))
    move_to(s, "chen", 4, 5)                # dist 2 — closing
    s.rng = FakeRNG(default=100)
    ai_turn(s, shemao)
    assert shemao.spearwall
    assert any(e["type"] == "stance" and e["kind"] == "spearwall" for e in s.events)


def test_gongzhai_battle_runs_clean():
    for seed in range(4):
        s = load_scenario("gongzhai", seed)
        r = run_battle(s, {"player": ai_turn, "enemy": ai_turn})
        assert r["winner"] in ("player", "enemy", "draw")
        for u in s.alive_units():
            assert not s.tiles[u.pos()].impassable


def test_garrison_holds_position():
    s = S()
    shemao = s.by_id("shemao")          # gate guard, garrison 1, home (6,3)
    assert shemao.garrison == 1 and shemao.home == (6, 3)
    park_others(s, {"shemao", "chen"}, where=(-4, 8))
    ready(shemao)
    move_to(s, "chen", 0, 4)            # foe far across the valley
    s.rng = FakeRNG(default=100)
    ai_turn(s, shemao)
    from sim.hexmath import hex_dist
    assert hex_dist(shemao, type("H", (), {"q": 6, "r": 3})) <= 1  # held the gate
    # but he still fights what comes to him
    move_to(s, "chen", 5, 3)            # adjacent now
    ready(shemao)
    n = len([e for e in s.events if e["type"] in ("hit", "miss")])
    ai_turn(s, shemao)
    assert len([e for e in s.events if e["type"] in ("hit", "miss")]) > n


# ---- the polearm sweepers (戟 / 大关刀) and the revised specials ----

def test_ji_reach_and_sweep():
    s = S()
    ji = ready(move_to(s, "zuanshan", 4, 4))
    park_others(s, {"zuanshan", "chen", "he", "shemao"})
    move_to(s, "chen", 6, 4)                 # dist 2 — in halberd reach
    from sim.commands import Strike, melee_targets
    assert [t.uid for t in melee_targets(s, ji)] == ["chen"]
    move_to(s, "he", 5, 4)                   # adjacent foe
    move_to(s, "shemao", 3, 4)               # adjacent friend — the swing is blind
    ji.skill = 1000
    n = len([e for e in s.events if e["type"] == "hit"])
    assert resolve(s, ji, Strike("", special=True)) is True
    swept = [e for e in s.events if e["type"] == "hit"][n:]
    assert sorted(e["dfn"] for e in swept) == ["he", "shemao"]  # chen at reach 2 is spared
    assert all(e["tag"] == "横扫" for e in swept)


def test_daguandao_chop_and_bleed():
    w = data.WEAPONS["daguandao"]
    _, body = compute_damage(30, 0, w, head=False)
    _, head = compute_damage(30, 0, w, head=True)
    assert head == int(body * 2.25 + 0.5)    # chop blade
    s = S()
    zhou = ready(move_to(s, "zhou", 0, 0))
    foe = move_to(s, "duyan", 1, 0)
    s.rng = FakeRNG([1, 100, 30])            # hit, body, dmg 30
    apply_hit(s, zhou, foe)
    assert foe.bleed == 2                    # the great blade cuts deep


def test_ai_demolish_smashes_heavy_armor():
    s = S()
    shi = ready(move_to(s, "shi", 6, 6))
    park_others(s, {"shi", "diao"})
    move_to(s, "diao", 6, 7)                 # tiejia 110 — worth the 碎甲
    s.rng = FakeRNG(default=100)
    ai_turn(s, shi)
    assert any(e.get("tag") == "碎甲" for e in s.events)


def test_ai_headhunt_cracks_bare_skull():
    s = S()
    whip = ready(move_to(s, "he", 6, 6))
    park_others(s, {"he", "yemao"})
    move_to(s, "yemao", 6, 7)                # no helmet — the whip goes upstairs
    s.rng = FakeRNG(default=100)
    ai_turn(s, whip)
    assert any(e.get("tag") == "兜头" for e in s.events)


def test_headhunt_whiff_drains_breath():
    """兜头 is a gamble: −15 to land, and the overswing costs 15 extra Breath."""
    s = S()
    whip = ready(move_to(s, "he", 6, 6))
    park_others(s, {"he", "duyan"})
    move_to(s, "duyan", 6, 7)
    from sim.commands import Strike
    s.rng = FakeRNG(default=100)             # whiff the gamble
    br0 = whip.breath
    assert resolve(s, whip, Strike("duyan", special=True)) is True
    assert [e for e in s.events if e["type"] == "miss"][-1]["tag"] == "兜头"
    assert br0 - whip.breath == 16 + 15      # swing cost + the overswing
    # a landed gamble pays only the swing cost
    ready(whip)
    s.rng = FakeRNG([1, 0, 20])
    br1 = whip.breath
    assert resolve(s, whip, Strike("duyan", special=True)) is True
    assert br1 - whip.breath == 16
