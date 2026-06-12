"""Overworld v0.3 — hex travel + the BB living-world layer on a FIXED map.

Same pointy-top axial grid and (col,row)→q convention as the battle maps.
A day grants MOVE_PER_DAY points: 官道 1/hex, plain 2, hills/forest 3,
rivers impassable except 渡口/桥. The BB layer (RESEARCH.md campaign digest):
roaming parties tick daily and intercept the column on contact; sight spots
parties and hidden lairs; provisions burn 1/day and refill in friendly
settlements; an encounter names the battle scenario seeded by the world hex,
overridden by anchored SITES (fixed-map design: 虎牢关 is always the duel,
滹沱桥 always the bridge fight) and by a lair's own scenario. Regions connect
at exit hexes (cross()). Headless and deterministic — world randomness draws
ONLY from the "worldgen" stream, so overworld play can never perturb combat.

Day semantics: world.day is the current day; everything that happens during
or at dusk of day N is stamped N; the clock then turns to N+1.
"""
import heapq
import json
import os
from dataclasses import dataclass, field

from .hexmath import hex_dist, neighbors
from .rng import Streams

WORLD_DIR = os.path.join(os.path.dirname(__file__), "..", "world")
SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "..", "scenarios")

MOVE_PER_DAY = 8     # 官道 ~8 hexes/day, open country ~4 — a hex ≈ half a 驿程
SIGHT = 3            # hexes; +1 ending the day on hills (BB: terrain sets sight)
PROVISIONS_MAX = 12  # days of supplies; refilled overnight in friendly settlements

COST = {"road": 1, "bridge": 1, "settlement": 1, "plain": 2, "ford": 2,
        "hills": 3, "forest": 3, "water": None}

HOSTILE = {"bandit", "raider"}
FRIENDLY_KINDS = {"city", "town", "village"}   # where the bureau can resupply


@dataclass
class WTile:
    q: int
    r: int
    terrain: str = "plain"

    @property
    def cost(self):
        return COST[self.terrain]


@dataclass
class WParty:
    pid: str
    name: str
    kind: str            # bandit | caravan | patrol | raider
    pos: tuple
    speed: int
    route: list = field(default_factory=list)   # settlement ids, looped
    home: tuple | None = None                   # bandit anchor
    prowl: int = 0                              # bandit leash radius
    leg: int = 0                                # next route waypoint index
    alive: bool = True                          # razing the lair disbands the band

    @property
    def hostile(self):
        return self.alive and self.kind in HOSTILE


@dataclass
class WorldState:
    spec: dict
    tiles: dict
    settlements: dict
    rng: Streams
    party: tuple
    day: int = 1
    provisions: int = PROVISIONS_MAX
    parties: list = field(default_factory=list)
    sites: dict = field(default_factory=dict)   # anchored set-pieces (虎牢关...)
    exits: dict = field(default_factory=dict)   # border hexes to neighbor regions
    spotted: set = field(default_factory=set)   # party/lair ids seen at least once
    destroyed: set = field(default_factory=set) # razed lairs
    events: list = field(default_factory=list)

    def emit(self, etype, **kw):
        self.events.append(dict(type=etype, day=self.day, **kw))

    def at_settlement(self):
        for s in self.settlements.values():
            if tuple(s["at"]) == self.party:
                return s
        return None


def load_world(world_id, seed=0):
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
        if s["kind"] not in KIND_GLYPH:
            raise ValueError(f"settlement '{s['id']}': unknown kind '{s['kind']}'")
        if s["at"] not in tiles or tiles[s["at"]].terrain == "water":
            raise ValueError(f"settlement '{s['id']}' off map or in a river")
        if not s.get("hidden"):
            tiles[s["at"]].terrain = "settlement"
        # a hidden lair's hex keeps its natural terrain — no cost hole, no
        # render tell, no pathfinder shortcut betraying the secret
        settlements[s["id"]] = s
    world = WorldState(spec=spec, tiles=tiles, settlements=settlements,
                       rng=Streams(seed), party=settlements[spec["start"]]["at"])
    for p in spec.get("parties") or []:
        if p["kind"] not in PARTY_GLYPH:
            raise ValueError(f"party '{p['id']}': unknown kind '{p['kind']}'")
        for wp in p.get("route") or []:
            if wp not in settlements:
                raise ValueError(f"party '{p['id']}': unknown waypoint '{wp}'")
        if p["kind"] == "bandit" and (not p.get("home") or p.get("prowl", 0) < 0):
            raise ValueError(f"bandit '{p['id']}' needs a home and prowl >= 0")
        anchor = settlements[p.get("home") or p["route"][0]]["at"]
        route = p.get("route") or []
        world.parties.append(WParty(
            pid=p["id"], name=p["name"], kind=p["kind"], pos=anchor,
            speed=p["speed"], route=route,
            home=anchor if p.get("home") else None, prowl=p.get("prowl", 0),
            leg=1 % len(route) if route else 0))   # day 1 marches, not idles
    for s in spec.get("sites") or []:
        s = dict(s, at=tuple(s["at"]))
        if s["at"] not in tiles or tiles[s["at"]].cost is None:
            raise ValueError(f"site '{s['id']}' off map or unenterable")
        world.sites[s["id"]] = s
    for x in spec.get("exits") or []:
        x = dict(x, at=tuple(x["at"]))
        if not os.path.exists(os.path.join(WORLD_DIR, x["to"] + ".json")):
            raise ValueError(f"exit '{x['id']}' leads to unknown region '{x['to']}'")
        world.exits[x["id"]] = x
    _validate_scenarios(world)
    _spot(world)  # what the bureau can see from the gate on day one
    return world


def _validate_scenarios(world):
    """Every battle a place can spawn must exist — fixed map, fail loud."""
    have = {f[:-5] for f in os.listdir(SCENARIO_DIR) if f.endswith(".json")}
    refs = list((world.spec.get("encounters") or {}).values())
    refs += [s["scenario"] for s in world.sites.values() if s.get("scenario")]
    refs += [s["scenario"] for s in world.settlements.values() if s.get("scenario")]
    missing = sorted(set(refs) - have)
    if missing:
        raise ValueError(f"world '{world.spec['id']}': unknown scenarios {missing}")


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


def sight_of(world):
    return SIGHT + (1 if world.tiles[world.party].terrain == "hills" else 0)


def _spot(world):
    """First sighting of parties and hidden lairs — BB's exploration reveal."""
    reach = sight_of(world)
    for p in world.parties:
        if (p.alive and p.pid not in world.spotted
                and hex_dist(p.pos, world.party) <= reach):
            world.spotted.add(p.pid)
            world.emit("spotted", what=p.pid, name=p.name, at=list(p.pos))
    for s in world.settlements.values():
        if (s.get("hidden") and s["id"] not in world.spotted
                and hex_dist(s["at"], world.party) <= reach):
            world.spotted.add(s["id"])
            world.emit("spotted", what=s["id"], name=s["name"], at=list(s["at"]))


def _step_toward(world, party, dest):
    """Advance a party up to its speed along the cheapest path."""
    if party.pos == dest:
        return
    costs, prev = dijkstra(world, party.pos)
    if dest not in costs:
        return
    path = path_to(prev, dest)
    budget, i = party.speed, 0
    while i + 1 < len(path) and budget >= world.tiles[path[i + 1]].cost:
        budget -= world.tiles[path[i + 1]].cost
        i += 1
    party.pos = path[i]


def _tick_parties(world):
    """One day of the living world. Deterministic: 'worldgen' draws only."""
    for p in world.parties:
        if not p.alive:
            continue
        if p.kind == "bandit":
            # prowl: a real day's march within the leash, drawn to the roads
            costs, _prev = dijkstra(world, p.pos)
            cands = [k for k, c in costs.items()
                     if c <= p.speed and hex_dist(k, p.home) <= p.prowl]
            roads = [k for k in cands if world.tiles[k].terrain == "road"]
            pool = roads * 2 + cands      # roads weighted 3× in total
            p.pos = pool[world.rng.rint(0, len(pool) - 1, "worldgen")]
        elif p.route:
            dest = world.settlements[p.route[p.leg]]["at"]
            _step_toward(world, p, dest)
            if p.pos == dest:
                p.leg = (p.leg + 1) % len(p.route)
    # the world grinds on without the player: bandits maul caravans they catch
    for p in world.parties:
        if p.kind == "caravan" and p.alive:
            for h in world.parties:
                if h.hostile and hex_dist(h.pos, p.pos) <= 1:
                    world.emit("caravan_attacked", caravan=p.pid, by=h.pid,
                               at=list(p.pos))


def _emit_encounter(world, p):
    """The world hex seeds the battle; an anchored site or a lair's own
    scenario overrides the terrain table — places mean something here."""
    enc = world.spec.get("encounters") or {}
    terrain = world.tiles[world.party].terrain
    site = next((s for s in world.sites.values() if s["at"] == world.party), None)
    lair = world.at_settlement()
    scen = ((site or {}).get("scenario") or (lair or {}).get("scenario")
            or enc.get(terrain) or enc.get("plain"))
    world.emit("encounter", party=p.pid, name=p.name, terrain=terrain,
               site=site["id"] if site else None, scenario=scen,
               at=list(world.party))


def _hostile_in_reach(world):
    return next((p for p in world.parties
                 if p.hostile and hex_dist(p.pos, world.party) <= 1), None)


def _burn_ration(world):
    world.provisions -= 1
    if world.provisions <= 0:
        world.provisions = 0
        world.emit("starving")


def _resupply(world):
    """Overnight restock — friendly gates only; ruins and 辽营 feed no one."""
    s = world.at_settlement()
    if (s and s["kind"] in FRIENDLY_KINDS and s["id"] not in world.destroyed):
        world.provisions = PROVISIONS_MAX
    return s


def _dusk(world):
    """Shared end-of-day bookkeeping, all stamped on the current day.
    Returns the interceptor, if any. The caller turns the clock."""
    _burn_ration(world)
    _tick_parties(world)
    _spot(world)
    p = _hostile_in_reach(world)
    if p:
        _emit_encounter(world, p)
    return p


def camp(world):
    """Hold position for a day (wait out a patrol, resupply in town)."""
    world.emit("camped", at=list(world.party))
    enc = _dusk(world)
    _resupply(world)
    world.day += 1
    return enc


def cross(world, exit_id):
    """Walk over a border hex into the neighbor region. The day clock and
    provisions travel with the bureau; the new region is a fresh fog."""
    x = world.exits[exit_id]
    if world.party != x["at"]:
        return None
    nxt = load_world(x["to"], seed=world.rng.seed)
    nxt.day = world.day
    nxt.provisions = world.provisions
    nxt.party = nxt.settlements[x["entry"]]["at"]
    nxt.events = world.events
    nxt.emit("crossed", to=x["to"], arrive=x["entry"])
    _spot(nxt)
    return nxt


def raze(world, lair_id):
    """Destroy a lair the bureau is standing on (post-battle hook). Disbands
    every band that called it home."""
    lair = world.settlements.get(lair_id)
    if (lair is None or lair_id in world.destroyed
            or tuple(lair["at"]) != world.party or lair["kind"] != "stronghold"):
        return False
    world.destroyed.add(lair_id)
    for p in world.parties:
        if p.home == tuple(lair["at"]):
            p.alive = False
    world.emit("razed", what=lair_id, name=lair["name"])
    return True


def travel(world, dest):
    """March day by day toward a hex or settlement id (hidden places can't be
    navigated to until discovered). A hostile within reach — at departure or
    on any step — halts the column. Returns days spent, or None if
    unreachable; the 'travel' event closes the journey, after any encounter."""
    if isinstance(dest, str):
        s = world.settlements[dest]
        if s.get("hidden") and dest not in world.spotted:
            return None                      # you can't ride to a rumor
        dest = s["at"]
    dest = tuple(dest)
    costs, prev = dijkstra(world, world.party)
    if dest not in costs:
        return None
    if dest == world.party:
        return 0
    path = path_to(prev, dest)
    days, i = 0, 0
    while i + 1 < len(path):
        budget = MOVE_PER_DAY
        interceptor = _hostile_in_reach(world)   # no slipping past at the gates
        while (not interceptor and i + 1 < len(path)
               and budget >= world.tiles[path[i + 1]].cost):
            budget -= world.tiles[path[i + 1]].cost
            i += 1
            world.party = path[i]
            _spot(world)                          # scouts watch while marching
            interceptor = _hostile_in_reach(world)  # BB: contact stops the column
        if budget == MOVE_PER_DAY and not interceptor:
            raise ValueError("terrain cost exceeds MOVE_PER_DAY — impassable map")
        days += 1
        if interceptor:
            # the battle eats the day; the world holds its breath until dusk
            _burn_ration(world)
            _emit_encounter(world, interceptor)
        else:
            interceptor = _dusk(world)
        s = _resupply(world)
        if interceptor or i + 1 >= len(path):
            world.emit("travel", to=list(world.party), days=days,
                       arrive=s["id"] if s else None,
                       intercepted=interceptor.pid if interceptor else None)
            world.day += 1
            return days
        world.day += 1
    return days


GLYPH = {"plain": "·", "road": "路", "hills": "山", "forest": "林",
         "water": "～", "ford": "渡", "bridge": "桥"}
KIND_GLYPH = {"city": "◎", "town": "○", "village": "村",
              "stronghold": "寨", "occupied": "辽"}
PARTY_GLYPH = {"bandit": "匪", "caravan": "商", "patrol": "巡", "raider": "骑"}


def render(world):
    """ASCII map — hidden lairs invisible until spotted, razed lairs are
    ruins (墟); party = 镖."""
    by_pos = {s["at"]: s for s in world.settlements.values()
              if not s.get("hidden") or s["id"] in world.spotted}
    site_pos = {s["at"]: s for s in world.sites.values()}
    seen_parties = {p.pos: p for p in world.parties
                    if p.alive and p.pid in world.spotted}
    out = []
    for r in range(world.spec["rows"]):
        row = [" "] if r % 2 else []
        for col in range(world.spec["cols"]):
            k = (col - (r >> 1), r)
            if k == world.party:
                row.append("镖")
            elif k in seen_parties:
                row.append(PARTY_GLYPH[seen_parties[k].kind])
            elif k in by_pos:
                s = by_pos[k]
                row.append("墟" if s["id"] in world.destroyed
                           else KIND_GLYPH[s["kind"]])
            elif k in site_pos:
                row.append(site_pos[k].get("glyph", "址"))
            else:
                # an undiscovered lair's hex reads as its natural ground
                row.append(GLYPH.get(world.tiles[k].terrain, "·"))
        out.append(" ".join(row))
    return "\n".join(out)
