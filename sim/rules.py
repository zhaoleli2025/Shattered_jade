"""Combat rules — straight port of the prototype's combat math (game.js).

Every formula here must match the reference implementation; tests pin the
known traces (e.g. 大锤 vs 110 armor: 0 / 3 / 34 HP over three average hits).
"""
from .hexmath import hex_dist, js_round, neighbors

MORALE_MULT = {"Steady": 1.0, "Wavering": 0.9, "Fleeing": 0.7}


def morale_mult(u):
    return MORALE_MULT[u.morale]


def exerts_zoc(u):
    return u.alive and u.wpn["kind"] == "melee" and u.morale != "Fleeing"


def double_grip(u):
    """BB: one-handed weapon + empty off-hand = +25% damage."""
    return u.wpn["kind"] == "melee" and u.wpn.get("hands") == 1 and not u.shield


def special_opts(sp):
    t = sp["type"]
    if t == "decap":
        return dict(mult=sp["dmg_mult"], fear_mod=-10, tag=sp["label"])
    if t == "demolish":
        return dict(armor_only=True, armor_mult=sp["armor_mult"], tag=sp["label"])
    if t == "aimed":
        return dict(acc_mod=sp["acc_bonus"], falloff=sp["falloff"], tag=sp["label"])
    if t == "sweep":
        return dict(acc_mod=sp["acc"], tag=sp["label"])
    if t == "headhunt":
        return dict(force_head=True, tag=sp["label"])
    return {}


def adjacent_units(state, q, r):
    out = []
    for nq, nr in neighbors(q, r):
        u = state.unit_at(nq, nr)
        if u:
            out.append(u)
    return out


def hit_breakdown(state, atk, dfn, opts=None):
    """Returns (parts, chance). parts: list of (label, value) — the F1 breakdown."""
    opts = opts or {}
    parts = []
    parts.append(("skill", js_round(atk.skill * morale_mult(atk))))
    parts.append(("weapon_acc", atk.wpn["acc"]))
    if opts.get("acc_mod"):
        parts.append(("special_acc", opts["acc_mod"]))

    # flails ignore the shield's base defense; a raised shield's extra still counts (BB)
    shield = dfn.shield or 0
    shield_bonus = ((0 if atk.wpn.get("ignore_shield") else shield)
                    + (shield if dfn.shieldwall else 0))
    parts.append(("defense", -js_round((dfn.dfn + shield_bonus) * morale_mult(dfn))))

    ta, td = state.tiles[atk.pos()], state.tiles[dfn.pos()]
    hdiff = ta.elev - td.elev
    if hdiff:
        parts.append(("height", hdiff * 10))

    if atk.wpn["kind"] == "melee" and hex_dist(atk, dfn) == 2:
        parts.append(("long_thrust", -15))  # BB: 2-hex attacks −15 unless mastered

    # 围攻 never applies to friendly fire (DESIGN §3.6 — BB's oversight, fixed)
    if atk.wpn["kind"] == "melee" and atk.side != dfn.side:
        adj_atk = sum(1 for u in adjacent_units(state, dfn.q, dfn.r)
                      if u.side == atk.side and u.wpn["kind"] == "melee"
                      and u.morale != "Fleeing")
        surround = max(0, adj_atk - 1) * 5
        if surround:
            parts.append(("surround", surround))

    if atk.wpn["kind"] == "ranged":
        dist = hex_dist(atk, dfn)
        fall = -max(0, dist - 1) * opts.get("falloff", atk.wpn["falloff"])
        if fall:
            parts.append(("falloff", fall))

    chance = max(5, min(95, js_round(sum(v for _, v in parts))))
    return parts, chance


def compute_damage(dmg, armor_before, wpn, head, opts=None):
    """Pure damage split — (armor_dmg, hp_dmg). No RNG; unit-testable traces."""
    opts = opts or {}
    if opts.get("armor_only"):  # 碎甲: pure armor destruction
        return min(armor_before, js_round(dmg * opts["armor_mult"])), 0
    armor_dmg = min(armor_before, js_round(dmg * wpn["armor_eff"]))
    hp_dmg = max(0, js_round(dmg * wpn["pierce"] - 0.1 * armor_before))
    if armor_dmg >= armor_before:  # armor destroyed → overflow
        hp_dmg += max(0, js_round(dmg * (1 - wpn["pierce"])) - armor_before)
    mult = 1.0
    if head:
        mult = 2.25 if wpn.get("chop") else 1.5
    return armor_dmg, js_round(hp_dmg * mult)


def apply_hit(state, atk, dfn, is_free=False, opts=None):
    """One attack resolution. Returns True on hit. Emits events."""
    opts = opts or {}
    parts, chance = hit_breakdown(state, atk, dfn, opts)
    roll = state.rng.d100()
    if roll > chance:
        state.emit("miss", atk=atk.uid, dfn=dfn.uid, chance=chance, roll=roll,
                   free=is_free, tag=opts.get("tag"))
        return False

    head_roll = state.rng.d100()
    head = bool(opts.get("force_head")) or (
        (not atk.wpn.get("no_head"))
        and head_roll <= 25 + atk.wpn.get("head_bonus", 0))

    dmg = state.rng.rint(atk.wpn["dmin"], atk.wpn["dmax"])
    if double_grip(atk):
        dmg = js_round(dmg * 1.25)
    if opts.get("mult"):
        dmg = js_round(dmg * opts["mult"])
    if is_free and opts.get("half_dmg"):
        dmg = js_round(dmg * 0.5)

    part = "armor_h" if head else "armor_b"
    armor_before = getattr(dfn, part)
    armor_dmg, hp_dmg = compute_damage(dmg, armor_before, atk.wpn, head, opts)
    setattr(dfn, part, max(0, armor_before - armor_dmg))
    dfn.hp = max(0, dfn.hp - hp_dmg)
    dfn.breath = max(0, dfn.breath - atk.wpn.get("breath_drain", 5))
    if atk.wpn.get("bleed") and hp_dmg >= 6:
        dfn.bleed = 2  # JS parity: set even on a killing blow (inert on the dead)

    state.emit("hit", atk=atk.uid, dfn=dfn.uid, chance=chance, roll=roll,
               head=head, dmg=dmg, armor_dmg=armor_dmg, hp_dmg=hp_dmg,
               free=is_free, tag=opts.get("tag"))

    if dfn.hp <= 0:
        kill(state, dfn, atk, opts.get("fear_mod", 0))
    elif hp_dmg >= 15:
        morale_check(state, dfn, -10, "big_hit")
    return True


def kill(state, u, killer, fear_mod=0):
    u.alive = False
    state.emit("death", unit=u.uid, killer=killer.uid if killer else None)
    for ally in state.alive_units(u.side):
        if hex_dist(ally, u) <= 5:
            morale_check(state, ally, (-15 if u.leader else 0) + fear_mod, "ally_died")
    check_end(state)


def morale_check(state, u, mod, reason):
    if not u.alive or u.morale == "Fleeing":
        return
    adj = sum(1 for x in adjacent_units(state, u.q, u.r) if x.side == u.side)
    target = u.resolve + adj * 3 + mod
    roll = state.rng.d100()
    if roll <= target:
        state.emit("morale_pass", unit=u.uid, target=target, roll=roll, reason=reason)
    else:
        u.morale = "Wavering" if u.morale == "Steady" else "Fleeing"
        if u.morale == "Fleeing":
            u.fled_rounds = 0
        state.emit("morale_fail", unit=u.uid, target=target, roll=roll,
                   reason=reason, now=u.morale)


def check_end(state):
    if state.over:
        return
    p = len(state.alive_units("player"))
    e = len(state.alive_units("enemy"))
    if p == 0 or e == 0:
        state.over = True
        state.winner = "enemy" if p == 0 else "player"
        state.emit("battle_end", winner=state.winner)
