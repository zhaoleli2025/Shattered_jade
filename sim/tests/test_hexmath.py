import json
import os

from sim.hexmath import DIRS, hex_dist, js_round, neighbors
from sim.state import SCENARIO_DIR, load_scenario


def test_distance_basics():
    assert hex_dist((0, 0), (0, 0)) == 0
    assert hex_dist((0, 0), (3, 0)) == 3
    assert hex_dist((0, 0), (0, 3)) == 3
    assert hex_dist((0, 0), (3, -3)) == 3
    assert hex_dist((2, 4), (8, 6)) == 8  # the prototype's leader-to-spearman line
    # symmetry
    assert hex_dist((1, 3), (4, -2)) == hex_dist((4, -2), (1, 3))


def test_neighbors():
    n = neighbors(0, 0)
    assert len(n) == 6 and len(set(n)) == 6
    assert all(hex_dist((0, 0), k) == 1 for k in n)
    assert len(DIRS) == 6


def test_js_round_half_away_from_zero():
    assert js_round(44.5) == 45  # Python's round() would give 44
    assert js_round(45.5) == 46
    assert js_round(55.8) == 56
    assert js_round(0.4) == 0


def test_scenarios_build_valid_maps():
    for scen_id in ("jiebiao", "gongzhai"):
        with open(os.path.join(SCENARIO_DIR, scen_id + ".json"), encoding="utf-8") as f:
            spec = json.load(f)
        s = load_scenario(scen_id)
        assert len(s.tiles) == spec["map"]["cols"] * spec["map"]["rows"]
        road = [tuple(k) for k in spec["map"]["road"]]
        for k in road:
            assert s.tiles[k].br_cost == 1 or s.tiles[k].terrain == "cart"
        for a, b in zip(road, road[1:]):
            assert hex_dist(a, b) == 1, f"{scen_id}: road gap {a}->{b}"
        # spawns on-map, unoccupied terrain, unique
        spawns = [tuple(u["spawn"]) for u in spec["units"]]
        assert len(spawns) == len(set(spawns))
        for k in spawns:
            assert k in s.tiles and not s.tiles[k].impassable
        assert len(s.units) == len(spec["units"])


def test_jiebiao_map_details():
    s = load_scenario("jiebiao")
    assert s.tiles[(1, 4)].impassable          # the 镖车
    assert s.tiles[(7, 4)].elev == 2
    assert s.tiles[(6, 5)].elev == 1
    assert s.tiles[(3, 1)].move_cost == 3      # forest


def test_gongzhai_mountain_village():
    s = load_scenario("gongzhai")
    # the mountain has three layers above the valley floor
    assert s.tiles[(7, 3)].elev == 3           # the summit (峰)
    assert s.tiles[(6, 4)].elev == 2           # village ground
    assert s.tiles[(5, 3)].elev == 1           # lower slope
    assert s.tiles[(2, 4)].elev == 0           # valley road
    walls = [t for t in s.tiles.values() if t.terrain == "wall"]
    assert len(walls) == 8 and all(t.impassable for t in walls)
    diao = s.by_id("diao")
    assert s.tiles[diao.pos()].elev == 3       # the chief holds the summit
    # the village interior is enterable ONLY through its two gates
    interior = {(7, 3), (8, 3), (6, 4), (7, 4)}
    entries = set()
    for iq, ir in interior:
        for k in [(iq + dq, ir + dr) for dq, dr in DIRS]:
            t = s.tiles.get(k)
            if t and k not in interior and not t.impassable:
                entries.add(k)
    assert entries == {(6, 3), (6, 5)}         # 正门 west, 后门 south
