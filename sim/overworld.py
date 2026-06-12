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

from . import data
from . import recruit as rc
from .hexmath import hex_dist, neighbors
from .rng import Streams

WORLD_DIR = os.path.join(os.path.dirname(__file__), "..", "world")
SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "..", "scenarios")

MOVE_PER_DAY = 8     # 官道 ~8 hexes/day, open country ~4 — a hex ≈ half a 驿程
SIGHT = 3            # hexes; +1 ending the day on hills (BB: terrain sets sight)
# provisions are now units, not days; the cap rides on the roster (see capacity)

COST = {"road": 1, "bridge": 1, "settlement": 1, "plain": 2, "ford": 2,
        "hills": 3, "forest": 3, "marsh": 4, "water": None, "mountains": None}
# mountains are walls (M&B: ranges channel armies through passes); a road
# mark carves the pass — the only way over a range

HOSTILE = {"bandit", "raider", "hunter"}
FRIENDLY_KINDS = {"city", "town", "village"}   # where the bureau can trade

# ---- the silver economy (M2): markets, escort contracts, the smith ----
GOLD_START = 100
# ---- the roster: each rider is a mule AND a mouth (BB upkeep) ----
CORE_ROSTER = ["wang", "liu", "shi", "yan"]   # the bureau's founding hands
PROVISION_BASE = 4         # the cart hauls this much even empty
CARRY_PER_HEAD = 2         # each rider shoulders this many 粮草
EAT_PER_HEAD = 1           # ...and eats this much a day
WAGE_PER_HEAD = 2          # 两/day, paid at dawn — the BB upkeep drain
HIRE_FEE = {"乡勇": 40, "刀手": 90, "弓手": 110}   # one-time, by recruit kind
RECRUIT_KINDS = {"乡勇": dict(wage=2), "刀手": dict(wage=4), "弓手": dict(wage=5)}
PROVISION_PRICE = {"city": 2, "town": 2, "village": 3}   # 两 per unit of 粮草
ESCORT_RATE = 40                                          # 两 per road-day
BOUNTY_PAY = 260                                          # 两 per razed lair
QUALITY_LADDER = ("fan", "liang", "jing", "zhen", "shen")
WAYLAY_SCEN = {"caravan": "jiebiao", "patrol": "duijue"}  # the bureau turns bandit
WAYLAY_LOOT = {"caravan": 150, "patrol": 60}
WAYLAY_INFAMY = {"caravan": 3, "patrol": 4}               # 官府闻之必怒 — and acts
INFAMY_PRICED = 3      # ≥: markets gouge (×1.5), the 镖单 thins to one offer
INFAMY_HUNTED = 6      # ≥: no jobs at all, and the 缉捕官军 rides out
ATONE_RATE = 40        # 两 per point of 恶名, paid at a city 衙门
REPAIR_RATE = 3        # points of armor/edge made whole per 两 (city or town)
SMITH_PRICE = {"liang": 100, "jing": 250, "zhen": 600, "shen": 1500}
GEAR_SLOTS = ("wpn_q", "wpn2_q", "armor_q", "helmet_q")


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
    provisions: int = PROVISION_BASE + CARRY_PER_HEAD * len(CORE_ROSTER)
    parties: list = field(default_factory=list)
    sites: dict = field(default_factory=dict)   # anchored set-pieces (虎牢关...)
    exits: dict = field(default_factory=dict)   # border hexes to neighbor regions
    spotted: set = field(default_factory=set)   # party/lair ids seen at least once
    destroyed: set = field(default_factory=set) # razed lairs
    gold: int = GOLD_START                      # 银两
    infamy: int = 0                             # 恶名 — the yamen remembers
    roster: list = field(default_factory=lambda: list(CORE_ROSTER))
    members: list = field(default_factory=list)  # hired hands: {name, kind, wage}

    def headcount(self):
        return len(self.roster) + len(self.members)

    def capacity(self):
        return PROVISION_BASE + CARRY_PER_HEAD * self.headcount()

    def daily_food(self):
        return EAT_PER_HEAD * self.headcount()

    def daily_wage(self):
        return (WAGE_PER_HEAD * len(self.roster)
                + sum(m["wage"] for m in self.members))
    gear: dict = field(default_factory=dict)    # hero id -> quality slots
    contract: dict | None = None                # one active job (BB rule)
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
              for kind in ("hills", "mountains", "marsh", "forest", "river",
                           "ford", "bridge", "road")}
    tiles = {}
    for r in range(spec["rows"]):
        for col in range(spec["cols"]):
            q = col - (r >> 1)
            terrain = "plain"          # later marks override earlier ones
            if (q, r) in marked["hills"]:
                terrain = "hills"
            if (q, r) in marked["mountains"]:
                terrain = "mountains"
            if (q, r) in marked["marsh"]:
                terrain = "marsh"
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
            raise ValueError(f"bandit '{p['id']}' needs a home and prowl >= 0")  # noqa
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
    # the heroes ride out with their template gear; the smith improves on it
    world.gear = {tpl["id"]: {k: tpl[k] for k in GEAR_SLOTS if tpl.get(k)}
                  for tpl in data.ROSTER if tpl["side"] == "player"}
    world.provisions = world.capacity()   # ride out with full packs
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


def dijkstra(world, start, goal=None):
    """Total move-point cost to every reachable hex. Returns (costs, prev).
    With a goal, stops as soon as the goal's cost is final (big-map speed)."""
    costs, prev = {start: 0}, {}
    frontier = [(0, start)]
    while frontier:
        c, k = heapq.heappop(frontier)
        if c > costs.get(k, 1 << 30):
            continue
        if k == goal:
            break
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
    costs, prev = dijkstra(world, party.pos, goal=dest)
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
        elif p.kind == "hunter":
            _step_toward(world, p, world.party)   # the writ names the bureau
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
    """A day's march: the whole company eats, and at dawn it is paid."""
    world.provisions -= world.daily_food()
    if world.provisions <= 0:
        world.provisions = 0
        world.emit("starving")
    wage = world.daily_wage()
    world.gold -= wage
    if world.gold < 0:
        world.gold = 0
        world.emit("unpaid", owed=wage)
    elif wage:
        world.emit("wages", paid=wage)


def _trade_post(world):
    """The friendly settlement underfoot, if any — where money talks."""
    s = world.at_settlement()
    if s and s["kind"] in FRIENDLY_KINDS and s["id"] not in world.destroyed:
        return s
    return None


def market_buy(world, days=None):
    """市集: provisions for silver. Buys up to `days` (default: fill up).
    Returns the number bought."""
    s = _trade_post(world)
    if not s:
        return 0
    price = PROVISION_PRICE[s["kind"]]
    if world.infamy >= INFAMY_PRICED:
        price = price + (price + 1) // 2      # outlaws pay gouged prices
    need = world.capacity() - world.provisions
    if days is not None:
        need = min(need, days)
    n = max(0, min(need, world.gold // price))
    if n:
        world.provisions += n
        world.gold -= n * price
        world.emit("market", bought=n, cost=n * price)
    return n


def jobs(world):
    """镖单: the board at a friendly settlement — escorts to the nearest
    cities/towns, plus a bounty on every discovered, standing lair.
    Deterministic: no dice, the map IS the job board."""
    s = _trade_post(world)
    if not s or world.infamy >= INFAMY_HUNTED:
        return []                              # nobody bonds cargo to the hunted
    costs, _prev = dijkstra(world, world.party)
    out = []
    dests = sorted((x for x in world.settlements.values()
                    if x["id"] != s["id"] and x["kind"] in ("city", "town")
                    and x["id"] not in world.destroyed
                    and tuple(x["at"]) in costs),
                   key=lambda x: costs[tuple(x["at"])])[:3]
    for d in dests[: 1 if world.infamy >= INFAMY_PRICED else 3]:
        days = max(1, -(-costs[tuple(d["at"])] // MOVE_PER_DAY))
        out.append(dict(kind="escort", to=d["id"], name=f"押镖至{d['name']}",
                        pay=days * ESCORT_RATE + 20, days=days))
    for lair in world.settlements.values():
        if (lair["kind"] == "stronghold" and lair["id"] in world.spotted
                and lair["id"] not in world.destroyed):
            out.append(dict(kind="bounty", target=lair["id"],
                            name=f"剿灭{lair['name']}", pay=BOUNTY_PAY))
    return out


def take_job(world, job):
    """One active contract at a time (BB rule)."""
    if world.contract:
        return False
    world.contract = dict(job)
    world.emit("contract_taken", job=dict(job))
    return True


def fail_contract(world):
    """A lost battle or abandoned cargo voids the bond (callers decide when)."""
    if world.contract:
        world.emit("contract_failed", job=world.contract)
        world.contract = None


def battle_wear(world, battle_state):
    """After a campaign battle the dents and dulled edges ride home: armor
    damage accumulates, weapon durability carries, until the smith mends it."""
    tpl = {p["id"]: p for p in data.ROSTER}
    for uid, g in world.gear.items():
        u = battle_state.by_id(uid)
        if u is None:
            continue
        main_id = tpl[uid]["wpn"]
        for w in (u.wpn, u.wpn2):
            if w is None:
                continue
            key = "wpn_dura" if w["id"] == main_id else "wpn2_dura"
            g[key] = w.get("dura_now")
        g["armor_dmg"] = g.get("armor_dmg", 0) + (u.armor_b0 - u.armor_b)
        g["helm_dmg"] = g.get("helm_dmg", 0) + (u.armor_h0 - u.armor_h)
    world.emit("wear_taken")


def repair_bill(world, uid):
    """What the smith would charge to make this hero's kit whole."""
    g = world.gear.get(uid)
    if g is None:
        return 0
    pts = g.get("armor_dmg", 0) + g.get("helm_dmg", 0)
    tpl = next(p for p in data.ROSTER if p["id"] == uid)
    for key, wid in (("wpn_dura", tpl["wpn"]), ("wpn2_dura", tpl.get("wpn2"))):
        if wid and g.get(key) is not None:
            pts += data.WEAPONS[wid]["dura"] - g[key]
    return -(-pts // REPAIR_RATE) if pts > 0 else 0


def smith_repair(world, uid):
    """修缮 (city or town): hammer the dents out, set the edge again."""
    s = _trade_post(world)
    if not s or s["kind"] not in ("city", "town") or uid not in world.gear:
        return 0
    bill = repair_bill(world, uid)
    if bill <= 0 or world.gold < bill:
        return 0
    world.gold -= bill
    g = world.gear[uid]
    g["armor_dmg"] = g["helm_dmg"] = 0
    g.pop("wpn_dura", None)
    g.pop("wpn2_dura", None)
    world.emit("repaired", hero=uid, cost=bill)
    return bill


def recruits_here(world):
    """The named candidates this settlement is offering this epoch (BB pool).
    Cached on the world so a look/gossip/exam persists between views until the
    pool refreshes or one is hired away."""
    s = _trade_post(world)
    if not s:
        return []
    epoch = world.day // rc.REFRESH_DAYS
    cache = getattr(world, "_pool", None)
    if not cache or cache[0] != (s["id"], epoch):
        fresh = rc.pool_for(world, s)
        taken = {m.get("rid") for m in world.members}
        fresh = [r for r in fresh if r["rid"] not in taken]
        world._pool = ((s["id"], epoch), fresh)
    return world._pool[1]


def gossip(world, rid):
    """茶馆: pay ~10% of the fee to learn a recruit's hidden 特性."""
    rec = next((r for r in recruits_here(world) if r["rid"] == rid), None)
    if rec is None or rec["reveal"] >= 1:
        return None
    cost = rc.gossip_cost(rec)
    if world.gold < cost:
        return None
    world.gold -= cost
    traits = rc.reveal_traits(rec)
    world.emit("gossip", rid=rid, cost=cost)
    return traits


def exam(world, rid):
    """医馆: pay to learn the talent COUNT and one attribute (never the map)."""
    rec = next((r for r in recruits_here(world) if r["rid"] == rid), None)
    if rec is None or rec["reveal"] >= 2:
        return None
    cost = rc.exam_cost(rec)
    if world.gold < cost:
        return None
    world.gold -= cost
    out = rc.reveal_talents(rec)
    world.emit("exam", rid=rid, cost=cost)
    return out


def hire(world, rid):
    """招募: take on a named hand — the fee now, the wage forever, and the
    whole character (stats/traits/talents) joins the company."""
    rec = next((r for r in recruits_here(world) if r["rid"] == rid), None)
    if rec is None or world.gold < rec["fee"]:
        return False
    world.gold -= rec["fee"]
    world.members.append(dict(rec))           # the full character rides along
    world._pool[1].remove(rec)                # gone from the board
    world.emit("hired", name=rec["name"], nick=rec["nick"],
               bg=rec["bg_name"], fee=rec["fee"])
    return True


def dismiss(world, index):
    """遣散: let a hired hand go (the founding core cannot be dismissed)."""
    if not (0 <= index < len(world.members)):
        return False
    m = world.members.pop(index)
    world.provisions = min(world.provisions, world.capacity())  # fewer packs
    world.emit("dismissed", name=m["name"])
    return True


def smith_upgrade(world, uid, slot):
    """铁匠铺 (cities only): raise one hero's gear one grade up the 品阶
    ladder. Returns the new grade, or None if it cannot be done."""
    s = _trade_post(world)
    if not s or s["kind"] != "city" or slot not in GEAR_SLOTS or uid not in world.gear:
        return None
    cur = world.gear[uid].get(slot, "fan")
    i = QUALITY_LADDER.index(cur) + 1
    if i >= len(QUALITY_LADDER):
        return None
    nxt = QUALITY_LADDER[i]
    price = SMITH_PRICE[nxt]
    if world.gold < price:
        return None
    world.gold -= price
    world.gear[uid][slot] = nxt
    world.emit("smith", hero=uid, slot=slot, grade=nxt, cost=price)
    return nxt


def _spawn_hunter(world):
    """恶名满贯: the 藩镇 issues a writ — one 缉捕官军 rides at a time."""
    if world.infamy < INFAMY_HUNTED:
        return
    if any(p.kind == "hunter" and p.alive for p in world.parties):
        return
    cities = [s for s in world.settlements.values()
              if s["kind"] == "city" and s["id"] not in world.destroyed]
    if not cities:
        return
    src = min(cities, key=lambda s: hex_dist(s["at"], world.party))
    world.parties.append(WParty(pid=f"hunter_{world.day}", name="缉捕官军",
                                kind="hunter", pos=tuple(src["at"]), speed=9))
    world.emit("hunted", source=src["id"])


def _dusk(world):
    """Shared end-of-day bookkeeping, all stamped on the current day.
    Returns the interceptor, if any. The caller turns the clock."""
    _burn_ration(world)
    _spawn_hunter(world)
    _tick_parties(world)
    _spot(world)
    p = _hostile_in_reach(world)
    if p:
        _emit_encounter(world, p)
    return p


def camp(world):
    """Hold position for a day (wait out a patrol; food still burns)."""
    world.emit("camped", at=list(world.party))
    enc = _dusk(world)
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
    if (world.contract and world.contract["kind"] == "bounty"
            and world.contract["target"] == lair_id):
        world.gold += world.contract["pay"]
        world.emit("contract_done", job=world.contract, pay=world.contract["pay"])
        world.contract = None
    return True


def waylay(world, pid):
    """The bureau turns bandit: ambush a caravan or patrol within reach.
    Returns the party, or None if it cannot be done. The battle itself and
    its consequences belong to the caller (plunder on victory)."""
    p = next((x for x in world.parties if x.pid == pid), None)
    if (p is None or not p.alive or p.kind not in WAYLAY_SCEN
            or hex_dist(p.pos, world.party) > 1):
        return None
    world.emit("waylay", party=pid, name=p.name, scenario=WAYLAY_SCEN[p.kind])
    return p


def plunder(world, pid):
    """Victory over a waylaid party: the spoils — and a name that darkens
    (infamy is the relations hook; consequences land with M2)."""
    p = next((x for x in world.parties if x.pid == pid), None)
    if p is None or not p.alive:
        return 0
    p.alive = False
    pay = WAYLAY_LOOT.get(p.kind, 0)
    world.gold += pay
    world.infamy += WAYLAY_INFAMY.get(p.kind, 0)
    world.emit("plunder", party=pid, name=p.name, pay=pay)
    world.emit("infamy", reason=f"劫{p.name}", infamy=world.infamy)
    return pay


def atone(world):
    """衙门 (cities): pay the 赎罪银 and the ledger closes."""
    s = _trade_post(world)
    if not s or s["kind"] != "city" or world.infamy <= 0:
        return 0
    cost = world.infamy * ATONE_RATE
    if world.gold < cost:
        return 0
    world.gold -= cost
    world.emit("atoned", cost=cost, infamy=world.infamy)
    world.infamy = 0
    return cost


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
        s = world.at_settlement()
        if (not interceptor and world.contract
                and world.contract["kind"] == "escort"
                and s and s["id"] == world.contract["to"]):
            pay = world.contract["pay"]
            world.gold += pay
            world.emit("contract_done", job=world.contract, pay=pay)
            world.contract = None
        if interceptor or i + 1 >= len(path):
            world.emit("travel", to=list(world.party), days=days,
                       arrive=s["id"] if s else None,
                       intercepted=interceptor.pid if interceptor else None)
            world.day += 1
            return days
        world.day += 1
    return days


GLYPH = {"plain": "·", "road": "路", "hills": "山", "forest": "林",
         "water": "～", "ford": "渡", "bridge": "桥", "mountains": "峰",
         "marsh": "沼"}
KIND_GLYPH = {"city": "◎", "town": "○", "village": "村",
              "stronghold": "寨", "occupied": "辽"}
PARTY_GLYPH = {"bandit": "匪", "caravan": "商", "patrol": "巡", "raider": "骑",
               "hunter": "捕"}


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
