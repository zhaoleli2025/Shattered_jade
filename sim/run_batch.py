"""AI-vs-AI batch runner — M0's balance instrument.

Usage:  python3 -m sim.run_batch [N] [scenario_id]      (from game01_demo/)
Runs N seeded battles of scenarios/<scenario_id>.json (default: jiebiao)
and prints win rates, casualties, weapon output.

NOTE for flat-map matchup batches: column-mirroring is not an exact isometry of
the offset hex grid, and first-best tie-breaks iterate east-first, so a single
orientation carries a spawn-side bias (~2:1 observed). Always run matchups in
BOTH orientations and average, or mirror through the map center in cube coords.
"""
import collections
import sys

from .ai import ai_turn
from .data import ROSTER
from .engine import run_battle
from .state import load_scenario


def weapon_at_event(unit, swaps_remaining):
    """Post-battle unit.wpn reflects the final state; walk swap parity back."""
    if swaps_remaining % 2 == 1 and unit.wpn2:
        return unit.wpn2
    return unit.wpn


def run(n=200, scenario="jiebiao"):
    wins = collections.Counter()
    rounds = []
    deaths = collections.Counter()
    dmg = collections.Counter()
    hits = collections.Counter()
    swings = collections.Counter()
    fielded = None

    for seed in range(n):
        s = load_scenario(scenario, seed)
        if fielded is None:
            fielded = [(u.uid, u.name, u.side) for u in s.units]
        result = run_battle(s, {"player": ai_turn, "enemy": ai_turn})
        wins[result["winner"]] += 1
        rounds.append(result["rounds"])
        for uid in result["dead"]:
            deaths[uid] += 1

        total_swaps = collections.Counter()
        for e in s.events:
            if e["type"] == "swap":
                total_swaps[e["unit"]] += 1
        seen = collections.Counter()
        for e in s.events:
            if e["type"] == "swap":
                seen[e["unit"]] += 1
            elif e["type"] in ("hit", "miss"):
                u = s.by_id(e["atk"])
                lbl = weapon_at_event(u, total_swaps[u.uid] - seen[u.uid])["label"]
                swings[lbl] += 1
                if e["type"] == "hit":
                    hits[lbl] += 1
                    dmg[lbl] += e["hp_dmg"] + e["armor_dmg"]

    print(f"=== {n} battles, scenario '{scenario}', AI vs AI ===")
    total = sum(wins.values())
    for side in ("player", "enemy", "draw"):
        print(f"  {side:>7}: {wins[side]:4d}  ({wins[side] / total:5.1%})")
    rounds.sort()
    print(f"  rounds: mean {sum(rounds) / len(rounds):.1f}  "
          f"median {rounds[len(rounds) // 2]}  max {rounds[-1]}")
    print("\n  death rate per unit:")
    for uid, name, side in fielded:
        mark = "镖" if side == "player" else "贼"
        print(f"    [{mark}] {name} ({uid}): {deaths[uid] / n:5.1%}")
    print("\n  weapon families — swings / hit% / damage:")
    for lbl, sw in swings.most_common():
        h = hits[lbl]
        print(f"    {lbl:>3}: {sw:6d} swings  {h / max(1, sw):5.1%} hit  "
              f"{dmg[lbl]:7d} dmg  ({dmg[lbl] / max(1, h):5.1f}/hit)")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 200,
        sys.argv[2] if len(sys.argv) > 2 else "jiebiao")
