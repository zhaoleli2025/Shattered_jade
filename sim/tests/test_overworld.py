"""Overworld v0: the 河北南部 test region — terrain, roads, rivers, the day clock."""
import pytest

from sim.overworld import MOVE_PER_DAY, dijkstra, load_world, path_to, travel


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
