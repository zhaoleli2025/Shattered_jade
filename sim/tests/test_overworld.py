"""Overworld v0: the 河北南部 test region — terrain, roads, rivers, the day clock."""
import json
import os

import pytest

from sim.overworld import (MOVE_PER_DAY, dijkstra, load_world, path_to, render,
                           travel)


def W():
    return load_world("hebei")


def test_region_loads_with_history_intact():
    w = W()
    assert (w.spec["cols"], w.spec["rows"]) == (24, 16)
    assert len(w.tiles) == 24 * 16
    # the ceded prefectures sit beyond the 拒马河 as occupied towns
    assert w.settlements["yingzhou"]["kind"] == "occupied"
    assert w.settlements["mozhou"]["kind"] == "occupied"
    assert w.party == w.settlements["zhenzhou"]["at"]


def test_all_settlements_reachable_from_zhenzhou():
    w = W()
    costs, _ = dijkstra(w, w.party)
    for s in w.settlements.values():
        assert s["at"] in costs, f"{s['id']} unreachable"


def test_roads_beat_open_country():
    w = W()
    costs, prev = dijkstra(w, w.settlements["zhenzhou"]["at"])
    path = path_to(prev, w.settlements["dingzhou"]["at"])
    kinds = [w.tiles[k].terrain for k in path[1:-1]]
    paved = sum(1 for k in kinds if k in ("road", "bridge", "settlement"))
    assert paved >= len(kinds) - 1     # the 官道 carries it (waystations count)
    # the 官道 makes 镇州→定州 a one-day ride; off-road it could not be
    assert costs[w.settlements["dingzhou"]["at"]] <= MOVE_PER_DAY + 2


def test_rivers_block_except_crossings():
    w = W()
    # the 滹沱河 row: water is unenterable, the bridge carries the road
    water = [t for t in w.tiles.values() if t.terrain == "water"]
    assert water and all(t.cost is None for t in water)
    path = path_to(dijkstra(w, w.settlements["zhenzhou"]["at"])[1],
                   w.settlements["dingzhou"]["at"])
    assert any(w.tiles[k].terrain == "bridge" for k in path), "must cross at 滹沱桥"


def test_travel_advances_the_day_clock():
    w = W()
    days = travel(w, "dingzhou")
    assert days >= 1 and w.day == 1 + days
    assert w.at_settlement()["id"] == "dingzhou"
    e = w.events[-1]
    assert e["type"] == "travel" and e["arrive"] == "dingzhou"
    # staying put costs nothing
    assert travel(w, "dingzhou") == 0


def test_frontier_crossable_only_at_the_fords():
    w = W()
    costs, prev = dijkstra(w, w.party)
    ying = w.settlements["yingzhou"]["at"]
    assert ying in costs                     # reachable — through a 渡口
    path = path_to(prev, ying)
    assert any(w.tiles[k].terrain == "ford" for k in path)


def test_unknown_world_fails_loud():
    with pytest.raises(FileNotFoundError):
        load_world("jiangnan")


# ---- the BB living-world layer (v0.2): parties, sight, provisions ----

def test_parties_tick_legally():
    w = W()
    band = next(p for p in w.parties if p.kind == "bandit")
    for _ in range(15):
        from sim.overworld import _tick_parties
        _tick_parties(w)
        for p in w.parties:
            assert p.pos in w.tiles and w.tiles[p.pos].cost is not None
        from sim.hexmath import hex_dist
        assert hex_dist(band.pos, band.home) <= band.prowl  # the leash holds


def test_caravan_walks_its_route():
    w = W()
    car = next(p for p in w.parties if p.kind == "caravan")
    visited = set()
    from sim.overworld import _tick_parties
    for _ in range(30):
        _tick_parties(w)
        for s in w.settlements.values():
            if car.pos == s["at"]:
                visited.add(s["id"])
    assert {"hejian", "cangzhou"} & visited  # it actually trades east


def test_hidden_lair_revealed_by_proximity():
    w = W()
    assert "寨" not in render(w)                       # 黑风寨 starts unknown
    travel(w, [-2, 8])                                  # ride into the 西山
    assert any(e["type"] == "spotted" and e["what"] == "heifengzhai"
               for e in w.events)
    assert "寨" in render(w)


def test_provisions_burn_and_refill():
    from sim.overworld import PROVISIONS_MAX, camp
    w = W()
    w.party = (3, 10)                                   # open country, no gates
    assert w.tiles[w.party].terrain == "plain"
    for _ in range(PROVISIONS_MAX + 2):
        camp(w)
    assert w.provisions == 0
    assert any(e["type"] == "starving" for e in w.events)
    travel(w, "zhaozhou")                               # nearest gates: resupply
    assert w.provisions == PROVISIONS_MAX
    camp(w)                                             # camping IN town restocks too
    assert w.provisions == PROVISIONS_MAX


def test_hostile_adjacency_forces_an_encounter():
    from sim.overworld import camp
    w = W()
    band = next(p for p in w.parties if p.kind == "bandit")
    nk = next(k for k in __import__("sim.hexmath", fromlist=["neighbors"])
              .neighbors(*w.party) if w.tiles[k].cost is not None)
    band.pos, band.home, band.prowl = nk, nk, 0         # pinned at the gates
    enc = camp(w)
    assert enc is band
    e = next(e for e in w.events if e["type"] == "encounter")
    # the world hex seeds the battle: at 镇州's gates that's the convoy ambush
    assert e["scenario"] == "jiebiao" and e["party"] == "heifeng_band"


def test_interception_halts_the_march():
    w = W()
    band = next(p for p in w.parties if p.kind == "bandit")
    # park the band astride the 官道 north of the bridge, leashed in place
    road_hex = (1, 11)
    assert w.tiles[road_hex].terrain == "road"
    band.pos, band.home, band.prowl = road_hex, road_hex, 0
    days = travel(w, "dingzhou")
    last = w.events[-1]
    assert last["type"] == "travel" and last["intercepted"] == "heifeng_band"
    assert w.party != w.settlements["dingzhou"]["at"]   # halted mid-march
    assert days == 1
    enc = next(e for e in w.events if e["type"] == "encounter")
    assert enc["scenario"] == "shouqiao"    # caught crossing 滹沱桥 — the bridge fight


def test_worldgen_stream_never_touches_combat_rolls():
    """Audit G16: the first second-stream consumer pins stream independence."""
    from sim.rng import Streams
    a = Streams(3)
    clean = [a.d100() for _ in range(20)]
    b = Streams(3)
    for _ in range(57):
        b.rint(0, 100, "worldgen")                      # overworld noise
    assert [b.d100() for _ in range(20)] == clean


def test_razing_the_lair_disbands_the_band():
    from sim.overworld import _tick_parties, raze
    w = W()
    band = next(p for p in w.parties if p.kind == "bandit")
    lair = w.settlements["heifengzhai"]
    w.party = lair["at"]                                # stormed it (battle won)
    assert raze(w, "heifengzhai") is True
    assert band.alive is False                          # the band is disbanded
    band.pos = lair["at"]
    for _ in range(5):
        _tick_parties(w)
    assert band.pos == lair["at"]                       # and never stirs again
    from sim.overworld import camp
    enc = camp(w)
    assert enc is None                                  # dead bands don't ambush
    assert raze(w, "heifengzhai") is False              # no double razing


# ---- v0.3: the fixed map — anchored sites, several regions ----

def test_site_overrides_terrain_encounter():
    from sim.overworld import camp
    w = W()
    ridge = w.sites["heifengling"]          # hills would say 攻寨; the site says duel
    assert w.tiles[ridge["at"]].terrain == "hills"
    w.party = ridge["at"]
    band = next(p for p in w.parties if p.kind == "bandit")
    band.pos, band.home, band.prowl = ridge["at"], ridge["at"], 0
    camp(w)
    e = next(e for e in w.events if e["type"] == "encounter")
    assert e["site"] == "heifengling" and e["scenario"] == "duijue"


def test_henan_loads_with_its_own_world():
    w = load_world("henan")
    assert w.settlements["bianzhou"]["kind"] == "city"
    assert "hulaoguan" in w.sites           # 虎牢关, the duel pass
    costs, _ = dijkstra(w, w.party)
    for s in w.settlements.values():
        assert s["at"] in costs, f"{s['id']} unreachable"


def test_crossing_into_henan_carries_the_clock():
    from sim.overworld import cross
    w = W()
    days = travel(w, w.exits["to_henan"]["at"])
    if w.events[-1]["intercepted"]:
        return                              # waylaid en route — a legal outcome
    prov, day = w.provisions, w.day
    w2 = cross(w, "to_henan")
    assert w2 is not None and w2.spec["id"] == "henan"
    assert w2.day == day and w2.provisions == prov
    assert w2.at_settlement()["id"] == "huazhou"
    assert w2.events[-1]["type"] == "crossed"
    # and the road home exists
    assert w2.exits["to_hebei"]["to"] == "hebei"


def test_world_rejects_unknown_scenario_refs(tmp_path, monkeypatch):
    import sim.overworld as ow
    spec = json.loads(open(os.path.join(ow.WORLD_DIR, "henan.json"),
                           encoding="utf-8").read())
    spec["encounters"]["road"] = "no_such_battle"
    (tmp_path / "henan.json").write_text(json.dumps(spec), encoding="utf-8")
    (tmp_path / "hebei.json").write_text("{}", encoding="utf-8")  # exit target exists
    monkeypatch.setattr(ow, "WORLD_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="no_such_battle"):
        load_world("henan")


def test_no_resupply_in_occupied_towns():
    from sim.overworld import camp
    w = W()
    w.party = w.settlements["mozhou"]["at"]             # 辽营 feeds no one
    w.provisions = 5
    camp(w)
    assert w.provisions == 4


def test_departure_beside_a_hostile_is_an_encounter():
    w = W()
    band = next(p for p in w.parties if p.kind == "bandit")
    nk = next(k for k in __import__("sim.hexmath", fromlist=["neighbors"])
              .neighbors(*w.party) if w.tiles[k].cost is not None)
    band.pos, band.home, band.prowl = nk, nk, 0
    days = travel(w, "dingzhou")                        # no slipping past the gates
    assert days == 1 and w.events[-1]["intercepted"] == "heifeng_band"
    enc = next(e for e in w.events if e["type"] == "encounter")
    assert enc["day"] == w.events[-1]["day"]            # one contact, one day stamp


def test_zhongyuan_the_grand_map():
    """v0.30: the M&B-style fixed realm — one continuous 56×36 中原."""
    w = load_world("zhongyuan")
    assert (w.spec["cols"], w.spec["rows"]) == (56, 36)
    costs, prev = dijkstra(w, w.party)
    for s in w.settlements.values():
        assert s["at"] in costs, f"{s['id']} unreachable"
    # the 太行 is a wall — 镇州→太原 must thread the 井陉 pass
    p = path_to(prev, w.settlements["taiyuan"]["at"])
    assert w.sites["jingxing"]["at"] in p
    mts = [t for t in w.tiles.values() if t.terrain == "mountains"]
    assert len(mts) > 100 and all(t.cost is None for t in mts)
    # the realm is big: 镇州→长安 is the better part of a week
    assert -(-costs[w.settlements["changan"]["at"]] // MOVE_PER_DAY) >= 5
    # every region of the plan is on the map
    regions = {s.get("region") for s in w.settlements.values()}
    assert {"河北", "河南", "河东", "关中", "山东", "幽云·辽"} <= regions


def test_realm_registry_is_consistent():
    """The modular realm: built areas load, links are symmetric sockets."""
    import sim.overworld as ow
    realm = json.load(open(os.path.join(ow.WORLD_DIR, "realm.json"), encoding="utf-8"))
    regions = {r["id"]: r for r in realm["regions"]}
    assert regions[realm["pilot"]]["status"] == "built"
    for r in realm["regions"]:
        for nbr in r["links"]:
            assert nbr in regions, f"{r['id']} links to unregistered '{nbr}'"
            assert r["id"] in regions[nbr]["links"], f"{r['id']}↔{nbr} not symmetric"
        if r["status"] == "built":
            load_world(r["id"])                 # plugged in and loadable
    load_world(realm["preview"])                # the composed grand map
