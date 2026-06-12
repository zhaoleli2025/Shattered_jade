"""Command-pattern turn resolution (DESIGN.md §7): every player/AI action is a
serializable command; resolve(state, unit, cmd) mutates state and emits events.
The skill-bar buttons in the prototype map 1:1 onto these commands."""
from dataclasses import dataclass

from .hexmath import hex_dist, neighbors
from .pathfind import breath_of_path, dijkstra, path_to
from .rules import apply_hit, exerts_zoc, special_opts

SWITCH_AP = 4
SHIELDWALL_AP, SHIELDWALL_BR = 4, 10


@dataclass
class Move:
    dest: tuple  # (q, r)


@dataclass
class Strike:
    target: str  # unit id
    special: bool = False


@dataclass
class Stance:
    kind: str  # "spearwall" | "shieldwall"


@dataclass
class Swap:
    pass


@dataclass
class EndTurn:
    pass


# ---- queries (shared by UI/AI legality and resolution) ----
def can_attack(u):
    return u.ap >= u.wpn["ap"] and u.breath >= u.wpn["br"]


def can_special(u):
    sp = u.wpn.get("special")
    return bool(sp and sp["type"] != "spearwall"
                and u.ap >= sp["ap"] and u.breath >= sp["br"])


def melee_targets(state, u):
    if u.wpn["kind"] != "melee":
        return []
    reach = u.wpn.get("reach", 1)
    foes = state.alive_units("enemy" if u.side == "player" else "player")
    return [e for e in foes if hex_dist(u, e) <= reach]


def ranged_targets(state, u):
    if u.wpn["kind"] != "ranged":
        return []
    rng_max = u.wpn["range"] + state.tiles[u.pos()].elev
    foes = state.alive_units("enemy" if u.side == "player" else "player")
    return [e for e in foes if 2 <= hex_dist(u, e) <= rng_max]  # no point-blank


def targets_of(state, u):
    return melee_targets(state, u) if u.wpn["kind"] == "melee" else ranged_targets(state, u)


# ---- resolution ----
def exec_move(state, u, path, total_cost):
    """AP/Breath for the whole intended path are spent up front (BB: a cancelled
    move still costs); ZoC strikes on leaving, spearwall strikes on approaching."""
    u.ap -= total_cost
    u.breath = max(0, u.breath - breath_of_path(state, path))
    struck, wall_struck = set(), set()
    for i in range(len(path) - 1):
        hq, hr = path[i]
        # leaving a hex adjacent to melee enemies → ALL of them strike first,
        # then any hit cancels the move (JS reference: collect, swing, then block)
        zocers = [e for nk in neighbors(hq, hr)
                  if (e := state.unit_at(*nk)) and e.side != u.side
                  and exerts_zoc(e) and e.uid not in struck]
        blocked = False
        for e in zocers:
            struck.add(e.uid)
            if apply_hit(state, e, u, is_free=True):
                blocked = True
            if not u.alive:
                return
        if blocked:
            state.emit("move_blocked", unit=u.uid, at=(hq, hr), by="zoc")
            return
        # approaching into a waiting spearwall → half-damage thrust; hit halts
        nq, nr = path[i + 1]
        halted = False
        for nk in neighbors(nq, nr):
            e = state.unit_at(*nk)
            if (e and e.side != u.side and e.spearwall and e.alive
                    and e.morale != "Fleeing" and e.uid not in wall_struck):
                wall_struck.add(e.uid)
                if apply_hit(state, e, u, is_free=True,
                             opts=dict(half_dmg=True, tag="spearwall")):
                    halted = True
                if not u.alive:
                    return
        if halted:
            state.emit("move_blocked", unit=u.uid, at=(hq, hr), by="spearwall")
            return
        u.q, u.r = nq, nr
    state.emit("moved", unit=u.uid, to=u.pos())


def _shot_wear(state, u):
    """BB: bows and crossbows pay 2 durability per shot, hit or miss."""
    if u.wpn["kind"] == "ranged" and u.wpn.get("dura_now") is not None:
        before = u.wpn["dura_now"]
        u.wpn["dura_now"] = max(0, before - 2)
        if before > 0 and u.wpn["dura_now"] == 0:
            state.emit("blunted", unit=u.uid, wpn=u.wpn["label"])


def resolve(state, u, cmd):
    """Returns True if the command was legal and executed."""
    if state.over or not u.alive or u.morale == "Fleeing":
        return False

    if isinstance(cmd, EndTurn):
        return True

    if isinstance(cmd, Move):
        costs, _brc, prev = dijkstra(state, u, u.ap, u.breath)
        if cmd.dest not in costs or costs[cmd.dest] == 0:
            return False
        exec_move(state, u, path_to(prev, cmd.dest), costs[cmd.dest])
        return True

    if isinstance(cmd, Strike):
        if cmd.special:
            sp = u.wpn.get("special")
            if not can_special(u):
                return False
            opts = special_opts(sp)
            if sp["type"] == "sweep":  # everyone adjacent, friend and foe
                if not targets_of(state, u):
                    return False  # JS UI requires an enemy in reach to swing
                u.ap -= sp["ap"]
                u.breath -= sp["br"]
                for nk in neighbors(u.q, u.r):
                    v = state.unit_at(*nk)
                    if v and v.alive:
                        apply_hit(state, u, v, opts=opts)
                return True
            t = state.by_id(cmd.target)
            if not (t and t.alive and any(x.uid == t.uid for x in targets_of(state, u))):
                return False
            u.ap -= sp["ap"]
            u.breath -= sp["br"]
            _shot_wear(state, u)
            landed = apply_hit(state, u, t, opts=opts)
            # 兜头 gamble: the overswing — a whiff drains extra Breath
            if not landed and opts.get("miss_br"):
                u.breath = max(0, u.breath - opts["miss_br"])
            return True
        if not can_attack(u):
            return False
        t = state.by_id(cmd.target)
        if not (t and t.alive and any(x.uid == t.uid for x in targets_of(state, u))):
            return False
        u.ap -= u.wpn["ap"]
        u.breath -= u.wpn["br"]
        _shot_wear(state, u)
        apply_hit(state, u, t)
        return True

    if isinstance(cmd, Stance):
        if cmd.kind == "spearwall":
            sp = u.wpn.get("special")
            if not (sp and sp["type"] == "spearwall" and not u.spearwall
                    and u.ap >= sp["ap"] and u.breath >= sp["br"]):
                return False
            u.ap -= sp["ap"]
            u.breath -= sp["br"]
            u.spearwall = True
            state.emit("stance", unit=u.uid, kind="spearwall")
            return True
        if cmd.kind == "shieldwall":
            if not (u.shield and not u.shieldwall
                    and u.ap >= SHIELDWALL_AP and u.breath >= SHIELDWALL_BR):
                return False
            u.ap -= SHIELDWALL_AP
            u.breath -= SHIELDWALL_BR
            u.shieldwall = True
            state.emit("stance", unit=u.uid, kind="shieldwall")
            return True
        return False

    if isinstance(cmd, Swap):
        if not u.wpn2 or u.ap < SWITCH_AP:
            return False
        u.wpn, u.wpn2 = u.wpn2, u.wpn
        u.ap -= SWITCH_AP
        u.spearwall = False  # can't hold the hedge with the spear stowed
        state.emit("swap", unit=u.uid, now=u.wpn["id"])
        return True

    return False
