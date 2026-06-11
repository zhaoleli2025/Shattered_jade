from sim import data
from sim.state import ambush_scenario
from sim.rules import (compute_damage, double_grip, hit_breakdown, special_opts)


def S():
    return ambush_scenario(seed=1)


def part(parts, label):
    return dict(parts).get(label, 0)


def move_to(state, uid, q, r):
    u = state.by_id(uid)
    u.q, u.r = q, r
    return u


def test_basic_breakdown_spear_vs_bandit():
    s = S()
    atk = move_to(s, "wang", 0, 0)
    dfn = move_to(s, "duyan", 1, 0)
    parts, chance = hit_breakdown(s, atk, dfn)
    assert part(parts, "skill") == 62
    assert part(parts, "weapon_acc") == 20
    assert part(parts, "defense") == -4
    assert chance == 78


def test_clamp_5_95():
    s = S()
    atk = move_to(s, "wang", 0, 0)
    dfn = move_to(s, "duyan", 1, 0)
    atk.skill = 500
    assert hit_breakdown(s, atk, dfn)[1] == 95
    atk.skill = -500
    assert hit_breakdown(s, atk, dfn)[1] == 5


def test_height_and_long_thrust():
    s = S()
    atk = move_to(s, "wang", 7, 4)   # hilltop, elev 2
    dfn = move_to(s, "duyan", 7, 6)  # flat, dist 2
    parts, _ = hit_breakdown(s, atk, dfn)
    assert part(parts, "height") == 20
    assert part(parts, "long_thrust") == -15  # spear reaching 2 hexes


def test_surround_is_per_extra_melee_attacker():
    s = S()
    dfn = move_to(s, "diao", 0, 0)
    a1 = move_to(s, "liu", 1, 0)
    move_to(s, "shi", 0, 1)        # second melee attacker adjacent
    move_to(s, "yan", -1, 1)       # archer adjacent — must NOT count
    parts, _ = hit_breakdown(s, a1, dfn)
    assert part(parts, "surround") == 5  # (2 melee − 1) × 5


def test_shieldwall_doubles_shield():
    s = S()
    atk = move_to(s, "liu", 0, 0)
    dfn = move_to(s, "diao", 1, 0)
    base = dict(hit_breakdown(s, atk, dfn)[0])["defense"]   # −(12+15)
    dfn.shieldwall = True
    walled = dict(hit_breakdown(s, atk, dfn)[0])["defense"]  # −(12+30)
    assert base == -27 and walled == -42


def test_ranged_falloff_and_aimed_override():
    s = S()
    atk = move_to(s, "yan", 0, 0)
    dfn = move_to(s, "duyan", 5, 0)
    parts, _ = hit_breakdown(s, atk, dfn)
    assert part(parts, "falloff") == -12  # (5−1) × 3
    opts = special_opts(atk.wpn["special"])
    parts2, _ = hit_breakdown(s, atk, dfn, opts)
    assert part(parts2, "falloff") == -8  # (5−1) × 2
    assert part(parts2, "special_acc") == 10


def test_hammer_vs_110_armor_trace():
    """The doc's verified trace: avg 34 dmg → armor 110→42→0, HP 0/3/34."""
    w = data.WEAPONS["dachui"]
    armor, expect = 110, [(68, 0), (42, 3), (0, 34)]
    for armor_dmg_exp, hp_exp in expect:
        armor_dmg, hp = compute_damage(34, armor, w, head=False)
        assert (armor_dmg, hp) == (armor_dmg_exp, hp_exp)
        armor -= armor_dmg


def test_demolish_is_pure_armor():
    w = data.WEAPONS["dachui"]
    opts = special_opts(w["special"])
    armor_dmg, hp = compute_damage(34, 110, w, head=False, opts=opts)
    assert armor_dmg == 102 and hp == 0
    # head demolish still does zero HP (no crit multiplier on nothing)
    armor_dmg, hp = compute_damage(34, 90, w, head=True, opts=opts)
    assert hp == 0


def test_head_multipliers():
    w = data.WEAPONS["jiuhuandao"]  # plain saber: head ×1.5
    _, hp_body = compute_damage(30, 0, w, head=False)
    _, hp_head = compute_damage(30, 0, w, head=True)
    assert hp_head == round(hp_body * 1.5)
    axe = data.WEAPONS["dafu"]      # chop: head ×2.25
    _, b = compute_damage(30, 0, axe, head=False)
    _, h = compute_damage(30, 0, axe, head=True)
    assert h == int(b * 2.25 + 0.5)


def test_dagger_puncture():
    w = data.WEAPONS["bishou"]
    armor_dmg, hp = compute_damage(20, 110, w, head=False)
    assert armor_dmg == 0          # 0% armor damage
    assert hp == 20 - 11           # 100% pierce − 10% of 110 armor
    assert w["no_head"]            # can't headshot (enforced in apply_hit)


def test_double_grip_eligibility():
    s = S()
    assert double_grip(s.by_id("shi")) is False     # 2H hammer
    assert double_grip(s.by_id("liu")) is False     # 1H + shield
    assert double_grip(s.by_id("duyan")) is True    # 1H, no shield
    assert double_grip(s.by_id("yan")) is False     # ranged
