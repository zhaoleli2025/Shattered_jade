"""Subsystem tests filling the adequacy-review gaps: bleed, routs, rallies,
escapes, apply-path modifiers, upkeep, initiative, AI hand rules.

FakeRNG scripts the dice: values are consumed in call order
(hit d100, head d100, damage rint, morale d100, ...). Default = always 100
(miss everything / fail every check)."""
from sim.ai import ai_turn
from sim.commands import EndTurn, Move, Strike, resolve
from sim.engine import initiative, run_battle, upkeep
from sim.rules import apply_hit, hit_breakdown, special_opts
from sim.state import ambush_scenario
from sim import data


class FakeRNG:
    def __init__(self, seq=None, default=100):
        self.seq = list(seq or [])
        self.default = default

    def _next(self):
        return self.seq.pop(0) if self.seq else self.default

    def d100(self, stream="combat"):
        return self._next()

    def rint(self, a, b, stream="combat"):
        return max(a, min(b, self._next()))


def S(seed=0):
    return ambush_scenario(seed)


def move_to(s, uid, q, r):
    u = s.by_id(uid)
    if u is None:  # not fielded by this scenario — summon from the roster
        from sim.data import ROSTER
        from sim.state import make_unit
        u = make_unit(next(t for t in ROSTER if t["id"] == uid), q, r)
        s.units.append(u)
    u.q, u.r = q, r
    return u


def ready(u):
    u.ap, u.breath = 9, u.breath_max
    return u


def park_others(s, keep, where=(-4, 8)):
    q0, r0 = where
    i = 0
    for u in s.units:
        if u.uid not in keep:
            u.q, u.r = q0 + i, r0
            i += 1


def hits(s):
    return [e for e in s.events if e["type"] == "hit"]


# ---------- bleed ----------
def test_bleed_applied_on_big_cut_not_small():
    s = S()
    liu = ready(move_to(s, "liu", 0, 0))
    foe = move_to(s, "duyan", 1, 0)
    s.rng = FakeRNG([1, 100, 30])  # hit, body, dmg 30 → hp_dmg 7 ≥ 6
    apply_hit(s, liu, foe)
    assert foe.bleed == 2
    foe.bleed = 0
    foe.armor_b, foe.hp = 25, 50
    s.rng = FakeRNG([1, 100, 22])  # hp_dmg 4 < 6
    apply_hit(s, liu, foe)
    assert foe.bleed == 0


def test_bleed_tick_kills_and_skips_turn():
    s = S()
    u = s.by_id("duyan")
    u.bleed, u.hp = 2, 4
    assert upkeep(s, u) is False
    assert u.hp == 0 and not u.alive
    kinds = [e["type"] for e in s.events]
    assert "bleed" in kinds and "death" in kinds
    death = next(e for e in s.events if e["type"] == "death")
    assert death["killer"] is None


# ---------- routs: rally / flee / escape ----------
def test_rally_succeeds_when_unmolested():
    s = S()
    u = move_to(s, "duyan", 6, 0)
    park_others(s, {"duyan"})
    u.morale, u.resolve = "Fleeing", 95
    s.rng = FakeRNG([50])
    assert upkeep(s, u) is True
    assert u.morale == "Wavering" and u.fled_rounds == 1
    assert any(e["type"] == "rally" for e in s.events)


def test_no_rally_with_enemy_adjacent():
    s = S()
    u = move_to(s, "duyan", 6, 0)
    park_others(s, {"duyan", "liu"})
    move_to(s, "liu", 7, 0)
    u.morale, u.resolve = "Fleeing", 95
    s.rng = FakeRNG([1])  # would pass — must not even be rolled
    assert upkeep(s, u) is False
    assert u.morale == "Fleeing"


def test_flee_reaches_edge_and_escapes():
    s = S()
    u = move_to(s, "duyan", 9, 4)
    park_others(s, {"duyan"}, where=(-4, 0))
    u.morale = "Fleeing"
    s.rng = FakeRNG(default=100)  # rally fails
    assert upkeep(s, u) is False
    assert u.escaped and not u.alive
    assert any(e["type"] == "escape" for e in s.events)
    assert s.col_of(u) == s.cols - 1


def test_all_escaped_side_loses():
    s = S()
    for other in s.alive_units("enemy"):
        if other.uid != "duyan":
            other.alive = False
    u = move_to(s, "duyan", 9, 4)
    u.morale = "Fleeing"
    u.ap = 9
    s.rng = FakeRNG(default=100)
    upkeep(s, u)
    assert s.over and s.winner == "player"


# ---------- apply-path modifiers ----------
def test_double_grip_bonus_in_event():
    s = S()
    atk = ready(move_to(s, "duyan", 0, 0))  # kandao, 1H, no shield
    move_to(s, "liu", 1, 0)
    s.rng = FakeRNG([1, 100, 24])
    apply_hit(s, atk, s.by_id("liu"))
    assert hits(s)[-1]["dmg"] == 30  # js_round(24 × 1.25)
    atk2 = ready(move_to(s, "shi", 4, 0))   # 2H hammer: no grip bonus
    move_to(s, "erma", 5, 0)
    s.rng = FakeRNG([1, 100, 30])
    apply_hit(s, atk2, s.by_id("erma"))
    assert hits(s)[-1]["dmg"] == 30


def test_breath_drain_on_defender():
    s = S()
    shi = ready(move_to(s, "shi", 0, 0))
    foe = move_to(s, "duyan", 1, 0)
    br0 = foe.breath
    s.rng = FakeRNG([1, 100, 30])
    apply_hit(s, shi, foe)
    assert br0 - foe.breath == 20  # 大锤 breath_drain
    liu = ready(move_to(s, "liu", 2, 0))
    foe2 = move_to(s, "erma", 3, 0)
    foe2.breath = 3
    s.rng = FakeRNG([1, 100, 22])
    apply_hit(s, liu, foe2)
    assert foe2.breath == 0  # floored, never negative


def test_demolish_full_apply_path():
    s = S()
    shi = ready(move_to(s, "shi", 0, 0))
    diao = move_to(s, "diao", 1, 0)
    n_events = len(s.events)
    s.rng = FakeRNG([1, 100, 34])
    apply_hit(s, shi, diao, opts=special_opts(shi.wpn["special"]))
    assert diao.armor_b == 8 and diao.hp == 70  # armor ×3, zero HP
    assert diao.bleed == 0
    assert diao.breath == diao.breath_max - 20  # drain still applies
    assert not any(e["type"].startswith("morale_") for e in s.events[n_events:])


def test_decap_fear_modifier_in_ripple():
    s = S()
    liu = ready(move_to(s, "liu", 3, 0))
    victim = move_to(s, "duyan", 4, 0)
    witness = move_to(s, "erma", 6, 0)  # dist 2 from victim, no adjacent allies
    park_others(s, {"liu", "duyan", "erma"})
    victim.hp = 5
    s.rng = FakeRNG([1, 100, 30, 100])  # kill, then witness's check fails
    apply_hit(s, liu, victim, opts=special_opts(liu.wpn["special"]))
    fail = next(e for e in s.events if e["type"] == "morale_fail")
    assert fail["unit"] == "erma" and fail["reason"] == "ally_died"
    assert fail["target"] == 38 - 10  # resolve 38 + 0 adj − 10 fear


def test_big_hit_morale_check():
    s = S()
    liu = ready(move_to(s, "liu", 0, 0))
    foe = move_to(s, "duyan", 1, 0)
    park_others(s, {"liu", "duyan"})
    foe.armor_b, foe.hp = 0, 100
    s.rng = FakeRNG([1, 100, 30, 100])  # hp_dmg 30 ≥ 15; check fails
    apply_hit(s, liu, foe)
    fail = next(e for e in s.events if e["type"] == "morale_fail")
    assert fail["reason"] == "big_hit" and foe.morale == "Wavering"


def test_morale_multipliers_in_breakdown():
    s = S()
    atk = move_to(s, "wang", 0, 0)
    dfn = move_to(s, "duyan", 1, 0)
    atk.morale, dfn.morale = "Wavering", "Fleeing"
    parts = dict(hit_breakdown(s, atk, dfn)[0])
    assert parts["skill"] == 56       # js_round(62 × 0.9)
    assert parts["defense"] == -3     # js_round(4 × 0.7)


def test_no_head_never_crits():
    s = S()
    atk = ready(move_to(s, "liu", 0, 0))
    atk.wpn = dict(data.WEAPONS["bishou"])
    foe = move_to(s, "duyan", 1, 0)
    s.rng = FakeRNG([1, 1, 20])  # head roll 1 would crit any other weapon
    apply_hit(s, atk, foe)
    e = hits(s)[-1]
    assert e["head"] is False and e["hp_dmg"] == 18  # 20 − 0.1×25, no ×1.5


# ---------- movement interactions ----------
def test_zoc_strikes_once_per_striker_per_move():
    s = S()
    park_others(s, {"liu", "duyan"})
    move_to(s, "duyan", 1, 0)
    liu = ready(move_to(s, "liu", 0, 0))
    s.rng = FakeRNG(default=100)  # all strikes miss
    resolve(s, liu, Move((1, 1)))  # path leaves two hexes in duyan's ZoC
    free = [e for e in s.events if e.get("free")]
    assert len(free) == 1 and liu.pos() == (1, 1)


def test_spearwall_strike_is_half_damage():
    s = S()
    park_others(s, {"wang", "duyan"})
    wang = ready(move_to(s, "wang", 0, 0))
    wang.spearwall = True
    wang.skill = 1000
    foe = ready(move_to(s, "duyan", 3, 0))
    s.rng = FakeRNG([1, 100, 30])
    resolve(s, foe, Move((1, 0)))
    e = next(e for e in s.events if e.get("tag") == "spearwall")
    assert e["dmg"] == 15  # js_round(30 × 0.5)
    assert foe.pos() == (2, 0)  # halted before entering reach


def test_zoc_all_strikers_swing_before_cancel():
    """The parity fix: both adjacent enemies strike even if the first hits."""
    s = S()
    park_others(s, {"liu", "duyan", "erma"})
    move_to(s, "duyan", 5, 4)
    move_to(s, "erma", 4, 5)
    liu = ready(move_to(s, "liu", 4, 4))  # adjacent to both, open ground
    s.rng = FakeRNG([1, 100, 20, 1, 100, 20])  # both strikes HIT
    liu.hp = 10 ** 6
    resolve(s, liu, Move((6, 3)))
    free = [e for e in s.events if e.get("free")]
    assert len(free) == 2  # second striker still swings
    assert liu.pos() == (4, 4)  # move cancelled


# ---------- engine contract ----------
def test_upkeep_contract():
    s = S()
    u = s.by_id("liu")
    u.shieldwall = u.spearwall = True
    u.breath, u.ap = 10, 0
    assert upkeep(s, u) is True
    assert (u.shieldwall, u.spearwall, u.breath, u.ap) == (False, False, 25, 9)
    u.breath = u.breath_max - 5
    upkeep(s, u)
    assert u.breath == u.breath_max  # regen capped


def test_initiative_tracks_breath_deficit():
    s = S()
    yan = s.by_id("yan")
    assert initiative(yan) == 112
    yan.breath -= 30
    assert initiative(yan) == 82
    assert initiative(s.by_id("duyan")) > initiative(yan)


def test_forced_draw_at_max_rounds():
    s = S()
    idle = lambda st, u: resolve(st, u, EndTurn())
    result = run_battle(s, {"player": idle, "enemy": idle}, max_rounds=3)
    assert result["winner"] == "draw" and result["rounds"] == 3
    ends = [e for e in s.events if e["type"] == "battle_end"]
    assert len(ends) == 1 and ends[0]["winner"] == "draw"


# ---------- AI hand rules ----------
def test_pinned_archer_swaps_and_fights():
    s = S()
    park_others(s, {"yan", "duyan"})
    yan = ready(move_to(s, "yan", 0, 0))
    move_to(s, "duyan", 1, 0)
    s.rng = FakeRNG(default=100)
    ai_turn(s, yan)
    assert yan.wpn["id"] == "bishou"
    assert any(e["type"] == "swap" for e in s.events)
    assert any(e["type"] in ("hit", "miss") and e["atk"] == "yan" for e in s.events)


def test_pinned_archer_without_budget_does_not_swap():
    s = S()
    park_others(s, {"yan", "duyan"})
    yan = move_to(s, "yan", 0, 0)
    yan.ap, yan.breath = 5, yan.breath_max  # < 4 + dagger's 4
    move_to(s, "duyan", 1, 0)
    s.rng = FakeRNG(default=100)
    ai_turn(s, yan)
    assert not any(e["type"] == "swap" for e in s.events)


def test_aimed_shot_through_resolve():
    s = S()
    park_others(s, {"yan", "duyan"})
    yan = ready(move_to(s, "yan", 0, 0))
    move_to(s, "duyan", 5, 0)
    s.rng = FakeRNG(default=100)
    assert resolve(s, yan, Strike("duyan", special=True)) is True
    e = s.events[-1]
    assert e["type"] == "miss" and e["chance"] == 64 and e["tag"] == "瞄准"
    assert yan.ap == 3 and yan.breath == yan.breath_max - 12


def test_surround_ignores_fleeing_allies():
    s = S()
    dfn = move_to(s, "diao", 0, 0)
    a1 = move_to(s, "liu", 1, 0)
    helper = move_to(s, "shi", 0, 1)
    parts = dict(hit_breakdown(s, a1, dfn)[0])
    assert parts.get("surround", 0) == 5
    helper.morale = "Fleeing"
    parts = dict(hit_breakdown(s, a1, dfn)[0])
    assert parts.get("surround", 0) == 0
