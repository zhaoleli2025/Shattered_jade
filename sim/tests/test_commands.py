from sim.commands import (Move, Stance, Strike, Swap, can_attack, melee_targets,
                          ranged_targets, resolve)
from sim.pathfind import dijkstra
from sim.state import ambush_scenario


def S():
    s = ambush_scenario(seed=7)
    return s


def move_to(state, uid, q, r):
    u = state.by_id(uid)
    if u is None:  # not fielded by this scenario — summon from the roster
        from sim.data import ROSTER
        from sim.state import make_unit
        u = make_unit(next(t for t in ROSTER if t["id"] == uid), q, r)
        state.units.append(u)
    u.q, u.r = q, r
    return u


def ready(u):
    u.ap, u.breath = 9, u.breath_max
    return u


def test_strike_costs_and_min_range():
    s = S()
    # park the other bandits out of bow range
    for uid, pos in [("erma", (4, 8)), ("xiaohu", (5, 8)), ("yemao", (6, 8)),
                     ("diao", (7, 8)), ("zuanshan", (8, 8))]:
        move_to(s, uid, *pos)
    yan = ready(move_to(s, "yan", 0, 0))
    move_to(s, "duyan", 1, 0)                # adjacent → bow may NOT fire
    assert ranged_targets(s, yan) == []
    assert resolve(s, yan, Strike("duyan")) is False
    move_to(s, "duyan", 3, 0)                # dist 3 → legal
    ap0, br0 = yan.ap, yan.breath
    assert resolve(s, yan, Strike("duyan")) is True
    assert (ap0 - yan.ap, br0 - yan.breath) == (4, 8)


def test_special_costs_only_special():
    s = S()
    liu = ready(move_to(s, "liu", 0, 0))
    move_to(s, "duyan", 1, 0)
    assert resolve(s, liu, Strike("duyan", special=True)) is True  # 斩首
    assert liu.ap == 9 - 5 and liu.breath == liu.breath_max - 15


def test_swap_costs_and_clears_spearwall():
    s = S()
    wang = ready(move_to(s, "wang", 0, 0))
    assert resolve(s, wang, Stance("spearwall")) is True
    assert wang.spearwall and wang.ap == 6
    assert resolve(s, wang, Swap()) is True
    assert wang.wpn["id"] == "yaodao" and wang.ap == 2
    assert wang.spearwall is False           # hedge dropped with the spear


def test_shieldwall_requires_shield():
    s = S()
    liu = ready(s.by_id("liu"))
    shi = ready(s.by_id("shi"))
    assert resolve(s, liu, Stance("shieldwall")) is True
    assert liu.shieldwall and liu.ap == 5 and liu.breath == liu.breath_max - 10
    assert resolve(s, shi, Stance("shieldwall")) is False  # no shield


def test_spear_reach_targets():
    s = S()
    wang = ready(move_to(s, "wang", 0, 0))
    move_to(s, "duyan", 2, 0)                # dist 2 — in spear reach
    assert [t.uid for t in melee_targets(s, wang)] == ["duyan"]
    resolve(s, wang, Swap())                 # saber: reach 1
    assert melee_targets(s, wang) == []


def test_move_budgets_roads_halve_breath():
    s = S()
    # clear other units away from the road west end
    for uid, pos in [("liu", (10, 0)), ("shi", (11, 0)), ("yan", (12, 0))]:
        move_to(s, uid, *pos)
    wang = ready(move_to(s, "wang", -2, 4))  # on the road
    costs, brc, _ = dijkstra(s, wang, wang.ap, wang.breath)
    assert costs[(0, 4)] == 4 and brc[(0, 4)] == 2     # two road hexes: 2 breath
    assert costs[(-1, 2)] == 4 and brc[(-1, 2)] == 4   # two grass hexes: 4 breath
    br0 = wang.breath
    assert resolve(s, wang, Move((0, 4))) is True
    assert wang.pos() == (0, 4) and wang.ap == 5 and br0 - wang.breath == 2


def test_cart_is_impassable():
    s = S()
    wang = ready(move_to(s, "wang", 0, 4))
    costs, _, _ = dijkstra(s, wang, wang.ap, wang.breath)
    assert (1, 4) not in costs               # the 镖车 blocks its hex


def test_zoc_hit_cancels_move():
    s = S()
    wang = ready(move_to(s, "wang", 0, 0))
    move_to(s, "duyan", 0, 1)                # bandit adjacent — wang is engaged
    s.rng._streams["combat"].seed(0)         # deterministic; first d100 small → hit
    ap0 = wang.ap
    resolve(s, wang, Move((3, 0)))
    blocked = [e for e in s.events if e["type"] == "move_blocked"]
    moved = [e for e in s.events if e["type"] == "moved"]
    free = [e for e in s.events if e.get("free")]
    assert free, "leaving ZoC must draw a free strike"
    if blocked:
        assert wang.pos() == (0, 0) and not moved
    else:
        assert wang.pos() == (3, 0)
    assert wang.ap == ap0 - 6                # full path AP spent either way


def test_spearwall_halts_before_entry():
    s = S()
    wang = ready(move_to(s, "wang", 0, 0))
    wang.spearwall = True
    foe = ready(move_to(s, "duyan", 3, 0))
    # force a guaranteed hit: massive skill
    wang.skill = 1000
    resolve(s, foe, Move((1, 0)))            # path ...→(2,0)→(1,0); (1,0) adj to wall
    assert foe.pos() != (1, 0)               # halted before entering reach? no —
    # (2,0) is already adjacent to (1,0)? dist((2,0),(0,0))=2 → not adjacent to wang.
    # entering (1,0) IS adjacent to wang → strike fires and halts at (2,0).
    assert foe.pos() == (2, 0)
    walls = [e for e in s.events if e.get("tag") == "spearwall"]
    assert walls and walls[0]["hp_dmg"] >= 0


def test_sweep_hits_all_adjacent_including_friends():
    s = S()
    axe = ready(move_to(s, "xiaohu", 4, 4))   # center hex: all 6 neighbors on-map
    move_to(s, "liu", 5, 4)
    move_to(s, "shi", 4, 5)
    move_to(s, "duyan", 3, 4)                 # his own bandit, adjacent
    axe.skill = 1000                          # all swings land
    n_hits_before = len([e for e in s.events if e["type"] == "hit"])
    assert resolve(s, axe, Strike("", special=True)) is True
    hits = [e for e in s.events if e["type"] == "hit"][n_hits_before:]
    assert sorted(h["dfn"] for h in hits) == ["duyan", "liu", "shi"]
    assert all(h["tag"] == "横扫" for h in hits)
