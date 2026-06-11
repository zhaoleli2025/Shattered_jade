"""Pointy-top axial hex math. Orientation and parity locked (DESIGN.md §7.1 M0)."""
import math

DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def hex_dist(a, b):
    """a, b: (q, r) tuples or objects with .q/.r."""
    aq, ar = (a.q, a.r) if hasattr(a, "q") else a
    bq, br = (b.q, b.r) if hasattr(b, "q") else b
    dq, dr = aq - bq, ar - br
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def neighbors(q, r):
    return [(q + dq, r + dr) for dq, dr in DIRS]


def js_round(x):
    """JS Math.round: half away from zero for positives (Python rounds half-even).

    Parity with the prototype requires this everywhere a fraction is rounded.
    """
    return math.floor(x + 0.5)
