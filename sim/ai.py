"""AI v0 — greedy + hand rules, ported from the prototype's aiTurn.

Deterministic (no temperature yet); any future randomness must use the "ai"
RNG stream so it never perturbs combat rolls."""
from .hexmath import hex_dist, neighbors
from .pathfind import dijkstra
from .commands import (SWITCH_AP, Stance, Strike, Swap, can_attack, can_special,
                       resolve, targets_of)
from .rules import hit_breakdown
from . import commands


def chance_vs(state, u, t):
    return hit_breakdown(state, u, t)[1]


def in_bounds(u, k):
    """Garrisoned units (scenario 'garrison': N) hold near their post."""
    return u.garrison is None or hex_dist(k, u.home) <= u.garrison


def ai_turn(state, u):
    for _safety in range(8):
        if state.over or not u.alive:
            return
        if u.morale == "Fleeing":  # routed mid-turn (ZoC strike) → stop acting
            return

        tgts = targets_of(state, u) if (can_attack(u) or can_special(u)) else []
        if tgts:
            tgts.sort(key=lambda x: (-chance_vs(state, u, x), x.hp))
            sp = u.wpn.get("special")
            if sp and can_special(u):
                if sp["type"] == "decap":
                    weak = next((x for x in tgts if x.hp / x.hp_max < 0.4), None)
                    if weak:
                        resolve(state, u, Strike(weak.uid, special=True))
                        continue
                elif sp["type"] == "sweep":
                    adj = [state.unit_at(*nk) for nk in neighbors(u.q, u.r)]
                    adj = [v for v in adj if v]
                    foes = sum(1 for v in adj if v.side != u.side)
                    friends = sum(1 for v in adj if v.side == u.side)
                    if foes >= 2 and friends == 0:
                        resolve(state, u, Strike("", special=True))
                        continue
                elif sp["type"] == "aimed":
                    if chance_vs(state, u, tgts[0]) < 55:
                        resolve(state, u, Strike(tgts[0].uid, special=True))
                        continue
            if can_attack(u):
                resolve(state, u, Strike(tgts[0].uid))
                continue
            return

        foes = state.alive_units("enemy" if u.side == "player" else "player")
        if not foes:
            return

        if u.wpn["kind"] == "ranged":
            nearest = min(foes, key=lambda f: hex_dist(u, f))
            dist = hex_dist(u, nearest)
            # rule: pinned archer draws the sidearm and fights
            if dist == 1 and u.wpn2 and u.ap >= SWITCH_AP + u.wpn2["ap"]:
                resolve(state, u, Swap())
                continue
            if dist < 3 and u.ap >= 2:  # rule: archers keep distance
                costs, _brc, _prev = dijkstra(state, u, u.ap, u.breath)
                best, best_score = None, -(1 << 30)
                for k in costs:
                    if not in_bounds(u, k):
                        continue
                    t = state.tiles[k]
                    dmin = min(hex_dist(t, f) for f in foes)
                    score = min(dmin, 6) + t.elev * 0.5
                    if score > best_score:
                        best_score, best = score, k
                if best and best != u.pos():
                    resolve(state, u, commands.Move(best))
                    continue
            # rule: out of bow range entirely → close in (fixes archer-stalemate draws)
            rng_max = u.wpn["range"] + state.tiles[u.pos()].elev
            if dist > rng_max and u.ap >= 2 and u.breath >= 1:
                costs, _brc, _prev = dijkstra(state, u, u.ap, u.breath)
                best, best_score = None, 1 << 30
                for k, c in costs.items():
                    if not in_bounds(u, k):
                        continue
                    t = state.tiles[k]
                    dmin = min(hex_dist(t, f) for f in foes)
                    score = dmin * 10 - t.elev * 3 + c * 0.1
                    if score < best_score:
                        best_score, best = score, k
                if best and best != u.pos():
                    resolve(state, u, commands.Move(best))
                    continue
            if targets_of(state, u) and can_attack(u):
                continue
            return

        # melee: out of attacks but enemy at hand → raise the shield
        adj_foe = any(hex_dist(u, f) == 1 for f in foes)
        if adj_foe and not can_attack(u):
            if resolve(state, u, Stance("shieldwall")):
                return
        # spear-bearer with enemies closing (2–3 hexes) → set the spearwall
        spw = u.wpn.get("special")
        if (spw and spw["type"] == "spearwall" and not u.spearwall
                and u.ap >= spw["ap"] and u.breath >= spw["br"]):
            nearest_d = min(hex_dist(u, f) for f in foes)
            if 2 <= nearest_d <= 3:
                resolve(state, u, Stance("spearwall"))
                return
        # melee: advance toward nearest foe, prefer high ground
        if u.ap < 2 or u.breath < 1:
            return
        costs, _brc, _prev = dijkstra(state, u, u.ap, u.breath)
        best, best_score = None, 1 << 30
        for k, c in costs.items():
            if not in_bounds(u, k):
                continue
            t = state.tiles[k]
            dmin = min(hex_dist(t, f) for f in foes)
            score = dmin * 10 - t.elev * 3 + c * 0.1
            if score < best_score:
                best_score, best = score, k
        if not best or best == u.pos():
            return
        resolve(state, u, commands.Move(best))
        if not targets_of(state, u) or not can_attack(u):
            return
