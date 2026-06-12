"""Overworld v0 — hex travel over a hand-authored region (M2 track).

Same pointy-top axial grid and (col,row)→q convention as the battle maps, so
the hex math is shared; movement is its own small Dijkstra (no units, no
Breath — a party token and a day clock). A day grants MOVE_PER_DAY points:
官道 1/hex, plain 2, hills/forest 3, bridges/fords cross the rivers, water is
otherwise impassable. Headless like the M0 sim: load → travel → events.
"""
import heapq
import json
import os
from dataclasses import dataclass, field

from .hexmath import neighbors

WORLD_DIR = os.path.join(os.path.dirname(__file__), "..", "world")

MOVE_PER_DAY = 8  # 官道 ~8 hexes/day, open country ~4 — a hex is roughly half a 驿程

COST = {"road": 1, "bridge": 1, "settlement": 1, "plain": 2, "ford": 2,
        "hills": 3, "forest": 3, "water": None}


@dataclass
class WTile:
    q: int
    r: int
    terrain: str = "plain"

    @property
    def cost(self):
        return COST[self.terrain]


@dataclass
class WorldState:
    spec: dict
    tiles: dict
    settlements: dict          # id -> settlement dict (incl. "at" tuple)
    party: tuple               # (q, r)
    day: int = 1
    events: list = field(default_factory=list)

    def emit(self, etype, **kw):
        self.events.append(dict(type=etype, day=self.day, **kw))

    def at_settlement(self):
        for s in self.settlements.values():
            if tuple(s["at"]) == self.party:
                return s
        return None


def load_world(world_id):
    with open(os.path.join(WORLD_DIR, world_id + ".json"), encoding="utf-8") as f:
        spec = json.load(f)
    marked = {kind: {tuple(k) for k in spec["map"].get(kind) or []}
              for kind in ("hills", "forest", "river", "ford", "bridge", "road")}
    tiles = {}
    for r in range(spec["rows"]):
        for col in range(spec["cols"]):
            q = col - (r >> 1)
            terrain = "plain"          # later marks override earlier ones
            if (q, r) in marked["hills"]:
                terrain = "hills"
            if (q, r) in marked["forest"]:
                terrain = "forest"
            if (q, r) in marked["road"]:
                terrain = "road"
            if (q, r) in marked["river"]:
                terrain = "water"
            if (q, r) in marked["ford"]:
                terrain = "ford"
            if (q, r) in marked["bridge"]:
                terrain = "bridge"
            tiles[(q, r)] = WTile(q, r, terrain)
    settlements = {}
    for s in spec["settlements"]:
        s = dict(s, at=tuple(s["at"]))
        if s["at"] not in tiles or tiles[s["at"]].terrain == "water":
            raise ValueError(f"settlement '{s['id']}' off map or in a river")
        tiles[s["at"]].terrain = "settlement"
        settlements[s["id"]] = s
    start = settlements[spec["start"]]["at"]
    return WorldState(spec=spec, tiles=tiles, settlements=settlements, party=start)


def dijkstra(world, start):
    """Total move-point cost to every reachable hex. Returns (costs, prev)."""
    costs, prev = {start: 0}, {}
    frontier = [(0, start)]
    while frontier:
        c, k = heapq.heappop(frontier)
        if c > costs.get(k, 1 << 30):
            continue
        for nk in neighbors(*k):
            t = world.tiles.get(nk)
            if t is None or t.cost is None:
                continue
            nc = c + t.cost
            if nc < costs.get(nk, 1 << 30):
                costs[nk], prev[nk] = nc, k
                heapq.heappush(frontier, (nc, nk))
    return costs, prev


def path_to(prev, dest):
    path = [dest]
    while path[0] in prev:
        path.insert(0, prev[path[0]])
    return path


def travel(world, dest):
    """Move the party to a hex or settlement id. Returns days spent, or None
    if unreachable. The day clock advances by ceil(cost / MOVE_PER_DAY)."""
    if isinstance(dest, str):
        dest = world.settlements[dest]["at"]
    dest = tuple(dest)
    costs, prev = dijkstra(world, world.party)
    if dest not in costs:
        return None
    cost = costs[dest]
    days = max(1, -(-cost // MOVE_PER_DAY)) if cost else 0
    world.party = dest
    world.day += days
    s = world.at_settlement()
    world.emit("travel", to=list(dest), cost=cost, days=days,
               arrive=s["id"] if s else None)
    return days


GLYPH = {"plain": "·", "road": "路", "hills": "山", "forest": "林",
         "water": "～", "ford": "渡", "bridge": "桥"}
KIND_GLYPH = {"city": "◎", "town": "○", "village": "村",
              "stronghold": "寨", "occupied": "辽"}


def render(world):
    """ASCII map — odd rows indented half a step, party = 镖."""
    by_pos = {s["at"]: s for s in world.settlements.values()}
    out = []
    for r in range(world.spec["rows"]):
        row = [" "] if r % 2 else []
        for col in range(world.spec["cols"]):
            k = (col - (r >> 1), r)
            if k == world.party:
                row.append("镖")
            elif k in by_pos:
                row.append(KIND_GLYPH[by_pos[k]["kind"]])
            else:
                row.append(GLYPH[world.tiles[k].terrain])
        out.append(" ".join(row))
    return "\n".join(out)
