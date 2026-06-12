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
    assert (w.spec["cols"], w.spec["rows"]) == (44, 40)   # v0.35: geo-faithful 河北
    assert len(w.tiles) == 44 * 40
    # 938: 瀛州 (seat: 河间) rides under the Liao banner
    assert w.settlements["yingzhou"]["fanzhen"] == "卢龙·辽"
    assert w.settlements["weizhou"]["fanzhen"] == "天雄军"
    assert w.settlements["zhenzhou"]["fanzhen"] == "成德军"
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
    water = [t for t in w.tiles.values() if t.terrain == "water"]
    assert water and all(t.cost is None for t in water)
    # 镇州 sits on the north bank — the road south crosses at the 滹沱 bridge
    path = path_to(dijkstra(w, w.settlements["zhenzhou"]["at"])[1],
                   w.settlements["zhaozhou"]["at"])
    assert any(w.tiles[k].terrain in ("bridge", "ford") for k in path)


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
    from sim.hexmath import neighbors
    from sim.overworld import _spot
    w = W()
    assert "寨" not in render(w)                       # 黑风寨 starts unknown
    lair = w.settlements["heifengzhai"]
    w.party = next(k for k in neighbors(*lair["at"])
                   if w.tiles.get(k) and w.tiles[k].cost is not None)
    band = next(p for p in w.parties if p.kind == "bandit")
    band.pos = w.party                                  # the band is out prowling
    _spot(w)                                            # ride up to it — revealed
    assert any(e["type"] == "spotted" and e["what"] == "heifengzhai"
               for e in w.events)
    assert "寨" in render(w)


def test_provisions_burn_and_the_market_feeds():
    from sim.overworld import camp, market_buy
    from sim.hexmath import hex_dist
    w = W()
    w.party = next(k for k, tl in sorted(w.tiles.items())   # open country, no gates
                   if tl.terrain == "plain"
                   and all(hex_dist(k, s["at"]) > 3 for s in w.settlements.values()))
    for _ in range(w.capacity() + 2):
        camp(w)
    assert w.provisions == 0
    assert any(e["type"] == "starving" for e in w.events)
    assert market_buy(w) == 0                           # no gates, no grain
    travel(w, "zhaozhou")
    assert w.provisions == 0                            # arrival alone feeds no one
    w.gold = 100                                        # wages emptied the purse
    cap, gold0 = w.capacity(), w.gold
    n = market_buy(w)                                   # 市集: silver for grain
    assert n == cap and w.provisions == cap
    assert w.gold == gold0 - n * 2


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
    # park the band astride the 滹沱 crossing south of 镇州, leashed in place
    _costs, prev = dijkstra(w, w.party)
    path = path_to(prev, w.settlements["zhaozhou"]["at"])
    cross = next(k for k in path if w.tiles[k].terrain in ("bridge", "ford"))
    band.pos, band.home, band.prowl = cross, cross, 0
    days = travel(w, "zhaozhou")
    last = w.events[-1]
    assert last["type"] == "travel" and last["intercepted"] == "heifeng_band"
    assert w.party != w.settlements["zhaozhou"]["at"]   # halted mid-march
    assert days == 1
    enc = next(e for e in w.events if e["type"] == "encounter")
    # contact happens at reach 1 — on the crossing itself or the approach road
    assert enc["scenario"] in ("shouqiao", "jiebiao")


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
    ridge = w.sites["heifengling"]          # whatever the ground says, the site says duel
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


def test_no_market_in_occupied_towns():
    from sim.overworld import camp, market_buy
    w = W()
    w.party = w.settlements["mozhou"]["at"]             # 辽营 feeds no one
    w.provisions = 5
    assert market_buy(w) == 0
    food0 = w.daily_food()
    camp(w)
    assert w.provisions == 5 - food0


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


# ---- the silver economy (v0.34): 镖单, 铁匠铺, gear riding to war ----

def test_escort_contract_pays_on_arrival():
    from sim.overworld import jobs, take_job
    w = W()
    board = jobs(w)
    escort = next(j for j in board if j["kind"] == "escort")
    assert take_job(w, escort) is True
    assert take_job(w, escort) is False                 # one bond at a time
    gold0 = w.gold
    travel(w, escort["to"])
    if w.at_settlement() and w.at_settlement()["id"] == escort["to"]:
        assert w.gold > gold0                           # paid, net of the day's wages
        assert w.contract is None
        assert any(e["type"] == "contract_done" for e in w.events)


def test_bounty_pays_on_razing():
    from sim.overworld import jobs, raze, take_job
    w = W()
    w.spotted.add("heifengzhai")                        # the lair is known
    bounty = next(j for j in jobs(w) if j["kind"] == "bounty")
    take_job(w, bounty)
    w.party = w.settlements["heifengzhai"]["at"]        # stormed it
    gold0 = w.gold
    assert raze(w, "heifengzhai")
    assert w.gold == gold0 + bounty["pay"] and w.contract is None


def test_smith_upgrades_ride_to_war():
    from sim.overworld import smith_upgrade
    from sim.state import load_scenario
    w = W()                                             # at 镇州, a city
    w.gold = 1000
    assert w.gear["wang"] == {}                         # 王铁枪 starts 凡品
    assert w.gear["liu"]["wpn_q"] == "jing"             # template gear seeds in
    assert smith_upgrade(w, "wang", "wpn_q") == "liang"
    assert smith_upgrade(w, "wang", "wpn_q") == "jing"
    assert w.gold == 1000 - 100 - 250
    w.gold = 0
    assert smith_upgrade(w, "wang", "wpn_q") is None    # no silver, no steel
    s = load_scenario("jiebiao", 0, gear=w.gear)
    assert s.by_id("wang").wpn["label"] == "精品·长枪"   # the work rides to war
    plain = load_scenario("jiebiao", 0)
    assert plain.by_id("wang").wpn["label"] == "长枪"


def test_smith_only_in_cities():
    from sim.overworld import smith_upgrade
    w = W()
    w.gold = 1000
    w.party = w.settlements["wangdu"]["at"]             # a village has no forge
    assert smith_upgrade(w, "wang", "wpn_q") is None


def test_waylay_turns_the_bureau_bandit():
    from sim.hexmath import neighbors
    from sim.overworld import plunder, waylay
    w = W()
    car = next(p for p in w.parties if p.kind == "caravan")
    car.pos = (w.party[0] + 5, w.party[1])              # somewhere down the road
    assert waylay(w, car.pid) is None                   # out of reach — no ambush
    car.pos = next(k for k in neighbors(*w.party) if w.tiles[k].cost is not None)
    p = waylay(w, car.pid)
    assert p is car
    e = next(e for e in w.events if e["type"] == "waylay")
    assert e["scenario"] == "jiebiao"                   # a convoy fight, roles reversed
    gold0 = w.gold
    assert plunder(w, car.pid) == 150
    assert w.gold == gold0 + 150 and car.alive is False
    assert any(e["type"] == "infamy" for e in w.events)
    band = next(p for p in w.parties if p.kind == "bandit")
    assert waylay(w, band.pid) is None                  # bandits get encounters, not waylays


def test_zhuozhou_sealed_behind_the_juma_crossings():
    """The 拒马 line holds: dam every crossing and 涿州 is cut off, while
    瀛莫 sit in open steppe south of the river — as 938 left them."""
    w = W()
    for t in w.tiles.values():
        if t.terrain in ("ford", "bridge"):
            t.terrain = "water"
    costs, _ = dijkstra(w, w.party)
    assert w.settlements["zhuozhou"]["at"] not in costs
    assert w.settlements["yingzhou"]["at"] in costs


def test_infamy_gouges_thins_then_hunts():
    """劫道 has consequences: prices gouge, the 镖单 thins, the writ goes out,
    and the 衙门 will settle it — for silver."""
    from sim.hexmath import hex_dist, neighbors
    from sim.overworld import (INFAMY_HUNTED, atone, camp, jobs, market_buy,
                               plunder, waylay)
    w = W()
    nk = lambda: next(k for k in neighbors(*w.party) if w.tiles[k].cost is not None)
    car = next(p for p in w.parties if p.kind == "caravan")
    car.pos = nk()
    waylay(w, car.pid); plunder(w, car.pid)
    assert w.infamy == 3
    assert len([j for j in jobs(w) if j["kind"] == "escort"]) == 1   # board thins
    w.provisions, gold0 = 0, w.gold
    assert market_buy(w, days=2) == 2
    assert gold0 - w.gold == 2 * 3                  # city price 2 → gouged 3 (no wage tick here)
    pat = next(p for p in w.parties if p.kind == "patrol")
    pat.pos = nk()
    waylay(w, pat.pid); plunder(w, pat.pid)
    assert w.infamy >= INFAMY_HUNTED
    assert jobs(w) == []                            # nobody bonds cargo to the hunted
    camp(w)                                         # dusk: the writ goes out
    hunter = next(p for p in w.parties if p.kind == "hunter" and p.alive)
    assert hunter.hostile and hex_dist(hunter.pos, w.party) <= 9
    w.gold = 1000
    assert atone(w) == w.infamy * 0 + 7 * 40        # 衙门: 赎罪银
    assert w.infamy == 0


def test_marsh_slows_but_carries():
    w = W()
    marsh = [t for t in w.tiles.values() if t.terrain == "marsh"]
    assert len(marsh) > 30 and all(t.cost == 4 for t in marsh)
    lair = w.settlements["dian_lair"]               # the 水寨 hides in the 淀
    costs, _ = dijkstra(w, w.party)
    assert tuple(lair["at"]) in costs


def test_wear_rides_home_and_the_smith_mends_it():
    from sim.overworld import battle_wear, repair_bill, smith_repair
    from sim.state import load_scenario
    w = W()
    s = load_scenario("jiebiao", 0, gear=w.gear)
    wang = s.by_id("wang")
    wang.wpn["dura_now"] -= 9                   # three armored strikes
    wang.armor_b -= 30                          # a dented cuirass
    battle_wear(w, s)
    g = w.gear["wang"]
    assert g["wpn_dura"] == wang.wpn["dura"] - 9 and g["armor_dmg"] == 30
    # the dents ride into the NEXT battle
    s2 = load_scenario("jiebiao", 1, gear=w.gear)
    wang2 = s2.by_id("wang")
    assert wang2.wpn["dura_now"] == wang2.wpn["dura"] - 9
    assert wang2.armor_b == wang2.armor_b0 and wang2.armor_b < 78  # dented start
    # the smith makes it whole — for silver
    bill = repair_bill(w, "wang")
    assert bill == -(-39 // 3)
    w.gold = 100
    assert smith_repair(w, "wang") == bill
    assert repair_bill(w, "wang") == 0
    s3 = load_scenario("jiebiao", 2, gear=w.gear)
    assert s3.by_id("wang").wpn["dura_now"] == s3.by_id("wang").wpn["dura"]


def test_repairs_in_towns_but_not_villages():
    from sim.overworld import smith_repair
    w = W()
    w.gear["wang"]["armor_dmg"] = 30
    w.gold = 100
    w.party = w.settlements["wangdu"]["at"]     # a village has no forge
    assert smith_repair(w, "wang") == 0
    w.party = w.settlements["dingzhou"]["at"]   # a town does
    assert smith_repair(w, "wang") > 0


def test_roster_carries_eats_and_is_paid():
    from sim.overworld import camp
    w = W()
    assert w.headcount() == 4 and w.capacity() == 12   # base 4 + 2×4
    assert w.daily_food() == 4 and w.daily_wage() == 8
    assert w.provisions == 12                           # rode out with full packs
    gold0, prov0 = w.gold, w.provisions
    camp(w)
    assert w.provisions == prov0 - 4                    # the company eats
    assert w.gold == gold0 - 8                          # the company is paid


def test_hire_grows_load_appetite_and_wage():
    from sim.overworld import dismiss, hire, recruits_here
    w = W()                                             # at 镇州, a city
    w.gold = 999
    cap0 = w.capacity()
    rec = recruits_here(w)[0]
    assert hire(w, rec["rid"]) is True
    assert w.headcount() == 5 and w.capacity() == cap0 + 2
    assert w.daily_food() == 5 and w.daily_wage() == 8 + rec["wage"]
    assert w.members[0]["name"] == rec["name"]
    assert dismiss(w, 0) is True                        # let him go
    assert w.headcount() == 4 and w.daily_wage() == 8


def test_villages_muster_softer_men():
    from sim.overworld import recruits_here
    w = W()
    w.party = w.settlements["wangdu"]["at"]             # a village
    bgs = {r["bg"] for r in recruits_here(w)}
    assert bgs <= {"tianong", "tuihuo", "liehu"}        # no 游侠/趟子手 in a hamlet


def test_unpaid_when_the_purse_runs_dry():
    from sim.overworld import camp
    w = W()
    w.gold = 3                                          # not enough for one day
    camp(w)
    assert w.gold == 0 and any(e["type"] == "unpaid" for e in w.events)
