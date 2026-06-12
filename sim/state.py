"""Battle state: tiles, units, events. Plain data; the view layer is elsewhere.

Scenarios are JSON files in scenarios/ — the single source of truth shared
with the web prototype (which fetches the same files)."""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field

from . import data
from .hexmath import js_round
from .rng import Streams

SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "..", "scenarios")


@dataclass
class Tile:
    q: int
    r: int
    elev: int = 0
    terrain: str = "grass"
    move_cost: int = 2
    br_cost: int = 2
    impassable: bool = False


@dataclass
class Unit:
    uid: str
    name: str
    glyph: str
    side: str
    q: int
    r: int
    hp_max: int
    skill: int
    dfn: int
    shield: int
    resolve: int
    init_base: int
    breath_max: int
    armor_b: int
    armor_h: int
    wpn: dict
    wpn2: dict | None = None
    leader: bool = False
    # dynamic
    hp: int = 0
    breath: int = 0
    ap: int = 0
    morale: str = "Steady"  # Steady | Wavering | Fleeing
    fled_rounds: int = 0
    bleed: int = 0
    alive: bool = True
    escaped: bool = False
    shieldwall: bool = False
    spearwall: bool = False
    armor_b0: int = 0
    armor_h0: int = 0
    armor_name: str = ""
    helm_name: str = ""
    garrison: int | None = None  # AI: won't advance beyond this many hexes from home
    home: tuple | None = None    # spawn hex, the garrison anchor

    def pos(self):
        return (self.q, self.r)


@dataclass
class BattleState:
    tiles: dict
    units: list
    rng: Streams
    cols: int = data.COLS
    rows: int = data.ROWS
    round: int = 0
    over: bool = False
    winner: str | None = None  # "player" | "enemy" | "draw"
    events: list = field(default_factory=list)

    # ---- queries ----
    def alive_units(self, side=None):
        return [u for u in self.units if u.alive and (side is None or u.side == side)]

    def unit_at(self, q, r):
        for u in self.units:
            if u.alive and u.q == q and u.r == r:
                return u
        return None

    def by_id(self, uid):
        for u in self.units:
            if u.uid == uid:
                return u
        return None

    def col_of(self, u):
        return u.q + (u.r >> 1)

    def emit(self, etype, **kw):
        self.events.append(dict(type=etype, round=self.round, **kw))


def tiles_from_spec(m):
    road = {tuple(k) for k in m.get("road") or []}
    forest = {tuple(k) for k in m.get("forest") or []}
    elev1 = {tuple(k) for k in m.get("elev1") or []}
    elev2 = {tuple(k) for k in m.get("elev2") or []}
    elev3 = {tuple(k) for k in m.get("elev3") or []}
    wall = {tuple(k) for k in m.get("wall") or []}
    water = {tuple(k) for k in m.get("water") or []}
    cart = tuple(m["cart"]) if m.get("cart") else None
    tiles = {}
    for r in range(m["rows"]):
        for col in range(m["cols"]):
            q = col - (r >> 1)
            terrain, elev, br_cost, impassable = "grass", 0, 2, False
            if (q, r) in forest:
                terrain = "forest"
            if (q, r) in elev1:
                terrain, elev = "hill", 1
            if (q, r) in elev2:
                terrain, elev = "hill", 2
            if (q, r) in elev3:
                terrain, elev = "hill", 3
            if (q, r) in road and terrain == "grass":
                terrain, br_cost = "road", 1  # roads: half Breath
            if (q, r) == cart:
                terrain, impassable = "cart", True
            if (q, r) in wall:  # 寨墙/栅栏 — nobody crosses, nobody stands here
                terrain, impassable = "wall", True
            if (q, r) in water:  # 河水 — same rule, different face
                terrain, impassable = "water", True
            tiles[(q, r)] = Tile(q, r, elev, terrain,
                                 3 if terrain == "forest" else 2, br_cost, impassable)
    return tiles


def load_scenario(scen_id, seed=0):
    """Build a battle from scenarios/<id>.json — same file the browser fetches."""
    path = os.path.join(SCENARIO_DIR, scen_id + ".json")
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    tpl_by_id = {t["id"]: t for t in data.ROSTER}
    unknown = [su["id"] for su in spec["units"] if su["id"] not in tpl_by_id]
    if unknown:
        raise ValueError(f"scenario '{scen_id}': unknown unit ids {unknown}")
    # JS parity: boot() rejects double-fielded templates (uids must be unique)
    ids = [su["id"] for su in spec["units"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"scenario '{scen_id}': duplicate unit ids {dupes}")
    units = []
    for su in spec["units"]:
        u = make_unit(tpl_by_id[su["id"]], *su["spawn"], overrides=su)
        u.garrison = su.get("garrison")
        units.append(u)
    return BattleState(tiles=tiles_from_spec(spec["map"]), units=units,
                       rng=Streams(seed),
                       cols=spec["map"]["cols"], rows=spec["map"]["rows"])


def quality_of(qid):
    """Look up a 品阶 grade; quality buys numbers, family buys verbs."""
    if qid not in data.QUALITY:
        raise ValueError(f"unknown quality id '{qid}' (valid: {list(data.QUALITY)})")
    return data.QUALITY[qid]


def q_round(x):
    """Half-up round at the table's 2-decimal precision: float dust would turn
    110×1.15 (= 126.4999…) into 126; snapping to 2 decimals first gives 127."""
    return js_round(js_round(x * 100) / 100)


def grade_weapon(wpn, gr):
    """Apply a quality grade to a (deep-copied) weapon dict in place."""
    wpn["dmin"] = q_round(wpn["dmin"] * gr["dmg"])
    wpn["dmax"] = q_round(wpn["dmax"] * gr["dmg"])
    wpn["br_tax"] = q_round(wpn["br_tax"] * gr["br_tax"])  # finer work hangs lighter
    wpn["acc"] += gr["acc"]
    if gr["rank"]:
        wpn["label"] = gr["label"] + "·" + wpn["label"]
    wpn["quality"] = gr["id"]
    return wpn


def grade_armor(piece, gr):
    """Quality-adjusted copy of an armor/helmet entry (base table untouched)."""
    piece = dict(piece)
    piece["protect"] = q_round(piece["protect"] * gr["protect"])
    piece["br_tax"] = q_round(piece["br_tax"] * gr["br_tax"])
    if gr["rank"]:
        piece["label"] = gr["label"] + "·" + piece["label"]
    piece["quality"] = gr["id"]  # mirror game.js gradeArmor
    return piece


def _grade_of(ov, tpl, k):
    """Override → template → 凡品, by ABSENCE only (None/missing falls back;
    a present-but-bogus value like "" must fail loud, never mask)."""
    v = ov.get(k)
    if v is None:
        v = tpl.get(k)
    return quality_of("fan" if v is None else v)


def make_unit(tpl, q, r, overrides=None):
    sq, sr = q, r
    ov = overrides or {}
    # eager for all four slots: a bad wpn2_q throws even with no sidearm
    gr = {k: _grade_of(ov, tpl, k)
          for k in ("wpn_q", "wpn2_q", "armor_q", "helmet_q")}
    body = grade_armor(data.ARMOR[tpl["armor"]], gr["armor_q"])
    helm = grade_armor(data.ARMOR[tpl["helmet"]], gr["helmet_q"])
    wpn = grade_weapon(copy.deepcopy(data.WEAPONS[tpl["wpn"]]), gr["wpn_q"])
    wpn2 = (grade_weapon(copy.deepcopy(data.WEAPONS[tpl["wpn2"]]), gr["wpn2_q"])
            if tpl.get("wpn2") else None)
    u = Unit(
        uid=tpl["id"], name=tpl["name"], glyph=tpl["glyph"], side=tpl["side"],
        q=sq, r=sr, hp_max=tpl["hp_max"], skill=tpl["skill"], dfn=tpl["dfn"],
        shield=tpl["shield"], resolve=tpl["resolve"], init_base=tpl["init_base"],
        # 坠气: everything strapped on drags on his wind — sidearm too,
        # even sheathed (换械 recomputes nothing)
        breath_max=tpl["breath_base"] - body["br_tax"] - helm["br_tax"]
        - wpn["br_tax"] - (wpn2["br_tax"] if wpn2 else 0),
        armor_b=body["protect"], armor_h=helm["protect"],
        armor_name=body["label"], helm_name=helm["label"],
        wpn=wpn, wpn2=wpn2,
        leader=tpl.get("leader", False),
    )
    u.hp, u.breath = u.hp_max, u.breath_max
    u.armor_b0, u.armor_h0 = u.armor_b, u.armor_h
    u.home = (sq, sr)
    return u


def ambush_scenario(seed=0):
    """The canonical 劫镖 fixture — identical to the web prototype's battle."""
    return load_scenario("jiebiao", seed)
