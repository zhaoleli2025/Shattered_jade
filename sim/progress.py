"""Leveling — BB attribute growth (DESIGN §4.4): every fighter has a per-attribute
baseline, an upper limit, and a per-level growth rate that talent stars accelerate.

Levels 1–11, XP 200→15000 (combat-fed). Each level raises 3 attributes by a roll
in that attribute's growth band; a starred attribute rolls higher (the band's top
lifts by the star count, ≈ +5 per star over a career — §4.3) and is capped at
base + room. Stars hidden at recruitment reveal themselves the first time leveling
rolls them — the discovery arc the F6 exam can never fully sell.
"""
from .recruit import ATTRS, ATTR_NAME

MAX_LEVEL = 11
# cumulative XP to BE a given level (index = level); combat-fed only (F9)
LEVEL_XP = [0, 0, 200, 550, 1050, 1750, 2700, 3950, 5550, 7550, 10000, 15000]

# per attribute: the level-up gain band (lo, hi) and the room above base it may
# climb (the upper limit). HP/Breath grow fast and far; 招架 slow and little.
GROW = {
    "hp":      dict(per=(3, 5), room=55),
    "breath":  dict(per=(3, 5), room=50),
    "skill":   dict(per=(1, 3), room=28),
    "resolve": dict(per=(2, 4), room=40),
    "init":    dict(per=(2, 4), room=40),
    "dfn":     dict(per=(1, 2), room=16),
}


def level_for_xp(xp):
    lvl = 1
    for L in range(2, MAX_LEVEL + 1):
        if xp >= LEVEL_XP[L]:
            lvl = L
    return lvl


def new_progress(base_stats, talents, level=1):
    """A fresh progression record. `base` is the floor and the cap anchor; `stats`
    is the living value that growth lifts."""
    return dict(level=level, xp=LEVEL_XP[level],
                stats={a: base_stats[a] for a in ATTRS},
                base={a: base_stats[a] for a in ATTRS},
                talents=dict(talents), revealed=[])


def cap_of(prog, attr):
    """The upper limit for this attribute on this fighter (base + its room)."""
    return prog["base"][attr] + GROW[attr]["room"]


def stars(prog, attr):
    return prog["talents"].get(attr, 0)


def _pick_three(prog, rng):
    """Which 3 attributes this level-up raises — starred ones favored, then the
    ones with the most room left (BB: you grow what has talent and headroom)."""
    def weight(a):
        room_left = cap_of(prog, a) - prog["stats"][a]
        return (1 + stars(prog, a) * 4) * (1 if room_left > 0 else 0) + room_left * 0.01
    ranked = sorted(ATTRS, key=lambda a: (-weight(a), rng.random()))
    return [a for a in ranked if cap_of(prog, a) > prog["stats"][a]][:3]


def level_up(prog, rng):
    """One level: raise 3 attributes, each by a star-boosted, capped roll."""
    gains = {}
    for a in _pick_three(prog, rng):
        lo, hi = GROW[a]["per"]
        g = rng.randint(lo, hi + stars(prog, a))      # stars lift the top
        g = min(g, cap_of(prog, a) - prog["stats"][a])  # never past the limit
        if g <= 0:
            continue
        prog["stats"][a] += g
        gains[a] = g
        if stars(prog, a) and a not in prog["revealed"]:
            prog["revealed"].append(a)                # the star shows itself
    prog["level"] += 1
    return gains


def award_xp(prog, amount, rng):
    """Combat earnings. Returns the list of per-level gain dicts (for the log)."""
    prog["xp"] += amount
    target = level_for_xp(prog["xp"])
    ups = []
    while prog["level"] < target:
        ups.append(level_up(prog, rng))
    return ups


def xp_to_next(prog):
    if prog["level"] >= MAX_LEVEL:
        return 0
    return LEVEL_XP[prog["level"] + 1] - prog["xp"]


def sheet(prog):
    """A readable progression line: level, xp-to-next, and stat/cap with revealed
    stars (the unrevealed ones stay hidden — the discovery is the point)."""
    rows = []
    for a in ATTRS:
        star = "★" * stars(prog, a) if a in prog["revealed"] else ""
        rows.append(f"{ATTR_NAME[a]}{prog['stats'][a]}/{cap_of(prog, a)}{star}")
    return dict(level=prog["level"], xp=prog["xp"], to_next=xp_to_next(prog),
                rows=rows)
