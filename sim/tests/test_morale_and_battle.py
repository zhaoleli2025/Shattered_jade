import collections

from sim.ai import ai_turn
from sim.engine import run_battle
from sim.rules import kill, morale_check
from sim.state import ambush_scenario


def S(seed=3):
    return ambush_scenario(seed)


def move_to(state, uid, q, r):
    u = state.by_id(uid)
    u.q, u.r = q, r
    return u


def test_death_ripples_within_5():
    s = S()
    victim = move_to(s, "duyan", 0, 0)
    near = move_to(s, "erma", 2, 0)     # dist 2 → checks
    far = move_to(s, "yemao", 9, 0)     # dist 9 → no check
    move_to(s, "xiaohu", 5, -2)
    move_to(s, "diao", 6, -2)
    victim.hp = 0
    kill(s, victim, s.by_id("liu"))
    checked = {e["unit"] for e in s.events if e["type"].startswith("morale_")}
    assert near.uid in checked or near.morale != "Steady"
    assert far.uid not in checked and far.morale == "Steady"


def test_fleeing_units_never_recheck():
    s = S()
    u = s.by_id("erma")
    u.morale = "Fleeing"
    n = len(s.events)
    morale_check(s, u, -50, "test")
    assert len(s.events) == n  # no event, no double-rout


def test_degradation_ladder():
    s = S()
    u = s.by_id("erma")
    u.resolve = -200  # always fails
    morale_check(s, u, 0, "t")
    assert u.morale == "Wavering"
    morale_check(s, u, 0, "t")
    assert u.morale == "Fleeing"


def test_full_battle_terminates_with_invariants():
    for seed in range(8):
        s = ambush_scenario(seed)
        result = run_battle(s, {"player": ai_turn, "enemy": ai_turn})
        assert result["winner"] in ("player", "enemy", "draw")
        assert result["rounds"] <= 100
        # invariants
        positions = [u.pos() for u in s.alive_units()]
        assert len(positions) == len(set(positions)), "two units share a hex"
        for u in s.units:
            if u.alive:
                assert u.hp > 0
            assert 0 <= u.breath <= u.breath_max
            assert u.armor_b >= 0 and u.armor_h >= 0


def test_determinism_same_seed_same_battle():
    logs = []
    for _ in range(2):
        s = ambush_scenario(seed=42)
        run_battle(s, {"player": ai_turn, "enemy": ai_turn})
        logs.append(s.events)
    assert logs[0] == logs[1]


def test_seeds_differ():
    winners = set()
    rounds = set()
    for seed in range(10):
        s = ambush_scenario(seed)
        r = run_battle(s, {"player": ai_turn, "enemy": ai_turn})
        winners.add(r["winner"])
        rounds.add(r["rounds"])
    assert len(rounds) > 1, "ten different seeds produced identical battles"


def test_hit_rate_matches_displayed_chance():
    """Statistical: a 70% attack should land ~70% over many rolls (seeded)."""
    from sim.rules import apply_hit, hit_breakdown
    s = S(seed=99)
    atk = move_to(s, "liu", 0, 0)
    dfn = move_to(s, "diao", 1, 0)
    atk.skill = 60 + 27 - 10  # tune so chance lands at a fixed value
    _, chance = hit_breakdown(s, atk, dfn)
    n, hits = 4000, 0
    for _ in range(n):
        dfn.hp, dfn.armor_b, dfn.armor_h, dfn.alive, dfn.morale = 10**6, 10**6, 10**6, True, "Steady"
        atk.morale = "Steady"
        if apply_hit(s, atk, dfn):
            hits += 1
    assert abs(hits / n - chance / 100) < 0.025


def test_head_rate_quarter():
    from sim.rules import apply_hit
    s = S(seed=5)
    atk = move_to(s, "liu", 0, 0)
    dfn = move_to(s, "diao", 1, 0)
    atk.skill = 10**4  # always hit
    heads = total = 0
    for _ in range(4000):
        dfn.hp, dfn.armor_b, dfn.armor_h, dfn.alive, dfn.morale = 10**6, 10**6, 10**6, True, "Steady"
        apply_hit(s, atk, dfn)
        total += 1
    heads = sum(1 for e in s.events if e["type"] == "hit" and e["head"])
    assert abs(heads / total - 0.25) < 0.02
