"""Movement search inside the sim core (never the engine's) — DESIGN.md §7.

Dijkstra over AP cost with a parallel Breath ledger; a hex is reachable only if
both budgets cover it. Mirrors game.js dijkstra (insertion-ordered, stable)."""
import heapq

from .hexmath import neighbors


def dijkstra(state, u, ap_budget, br_budget):
    """Returns (costs, brc, prev) keyed by (q, r). Start cost 0."""
    start = u.pos()
    costs = {start: 0}
    brc = {start: 0}
    prev = {}
    counter = 0  # FIFO tie-break → matches the JS stable sort ordering
    frontier = [(0, 0, start)]
    while frontier:
        c, _, k = heapq.heappop(frontier)
        if c > costs.get(k, 1 << 30):
            continue
        t = state.tiles[k]
        for nk in neighbors(t.q, t.r):
            nt = state.tiles.get(nk)
            if nt is None or nt.impassable or state.unit_at(*nk):
                continue
            climb = max(0, nt.elev - t.elev)
            nc = c + nt.move_cost + climb
            nb = brc[k] + nt.br_cost
            if nc <= ap_budget and nb <= br_budget and nc < costs.get(nk, 1 << 30):
                costs[nk] = nc
                brc[nk] = nb
                prev[nk] = k
                counter += 1
                heapq.heappush(frontier, (nc, counter, nk))
    return costs, brc, prev


def path_to(prev, dest):
    path = [dest]
    while path[0] in prev:
        path.insert(0, prev[path[0]])
    return path  # includes start


def breath_of_path(state, path):
    return sum(state.tiles[k].br_cost for k in path[1:])
