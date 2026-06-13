"""Enlarge the 河北南部 pilot map — a one-time, idempotent data migration.

Three things at once (the user asked for all of them):
  1. RENDER bigger — sets spec.hexSize so world.js draws the hexes/units larger
     and easier to click (the page also widens its zoom-out range).
  2. EXPAND the territory — adds the 渤海 coast east of 沧州 with 无棣, two more
     河北 seats (祁州/蠡州) to fill the roomier interior, and a fresh 绿林 lair
     (葫芦谷寨) + its band, so the bigger map has more to do.
  3. SCALE the grid ×2 — every terrain hex and every `at` is 2×-upscaled by the
     2×2-block map  (q,r) → {(2q+a, 2r+b) : a,b∈{0,1}}.  Because that block map is
     a bijection on the hex plane, an upscaled hex (2q+a,2r+b) lands in terrain
     array X iff the original (q,r) did — so EVERY upscaled hex inherits the exact
     terrain of its source hex.  The map is a perfect 2× nearest-neighbour upscale:
     passability, river crossings and connectivity are preserved exactly; only the
     distances double (which is the point — longer journeys, a bigger region).

Run ONCE from game01_demo/:   python3 tools/enlarge_hebei.py
git is the backup (git show HEAD:world/hebei.json).  Re-running is a no-op: the
`_enlarged` marker guards against double-scaling.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEBEI = os.path.join(ROOT, "world", "hebei.json")

TERRAIN_KEYS = ["hills", "mountains", "marsh", "forest", "river", "ford", "bridge", "road"]
# precedence must mirror sim/overworld.load_world / world.js buildWorld exactly
PRECEDENCE = ["hills", "mountains", "marsh", "forest", "road", "river", "ford", "bridge"]
PASSABLE_BLOCK = {"water", "mountains"}     # where settlements/roads must not go
HEX_SIZE = 28                                # bigger hexes for the enlarged board


def block(q, r):
    """The 2×2 hex block a source hex maps to under the ×2 upscale."""
    return [(2 * q, 2 * r), (2 * q + 1, 2 * r), (2 * q, 2 * r + 1), (2 * q + 1, 2 * r + 1)]


def hex_line(a, b):
    """Connected axial path a→b (cube-coordinate interpolation, standard hex line)."""
    (q0, r0), (q1, r1) = a, b
    x0, z0, y0 = q0, r0, -q0 - r0
    x1, z1, y1 = q1, r1, -q1 - r1
    n = max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    out = []
    for i in range(n + 1):
        t = i / n if n else 0
        xs, ys, zs = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
        rx, ry, rz = round(xs), round(ys), round(zs)
        dx, dy, dz = abs(rx - xs), abs(ry - ys), abs(rz - zs)
        if dx > dy and dx > dz:
            rx = -ry - rz
        elif dy > dz:
            ry = -rx - rz
        else:
            rz = -rx - ry
        out.append((rx, rz))     # cube (x,z) → axial (q,r)
    return out


def main():
    with open(HEBEI, encoding="utf-8") as f:
        spec = json.load(f)
    if spec.get("_enlarged"):
        print("hebei.json already enlarged (_enlarged marker present) — nothing to do.")
        return

    # ---- 1+3: ×2 block-upscale every terrain array and every `at` coordinate ----
    new_map = {}
    for key, cells in spec["map"].items():
        seen, upscaled = set(), []
        src = cells or []
        for q, r in src:
            for h in block(q, r):
                if h not in seen:
                    seen.add(h)
                    upscaled.append([h[0], h[1]])
        new_map[key] = upscaled
    spec["map"] = new_map

    def scale_at(node):
        node["at"] = [2 * node["at"][0], 2 * node["at"][1]]

    for s in spec.get("settlements", []):
        scale_at(s)
    for s in spec.get("sites", []):
        scale_at(s)
    for lb in spec.get("labels", []):
        scale_at(lb)
    for x in spec.get("exits", []):
        scale_at(x)

    # ---- build the upscaled terrain grid so expansion lands on legal ground ----
    marks = {k: {tuple(c) for c in spec["map"].get(k, [])} for k in TERRAIN_KEYS}

    def terrain_of(q, r):
        t = "plain"
        for k in PRECEDENCE:
            if (q, r) in marks[k]:
                t = "water" if k == "river" else k
        return t

    occupied = {tuple(s["at"]) for s in spec["settlements"]}
    occupied |= {tuple(s["at"]) for s in spec["sites"]}

    def add_mark(kind, q, r):
        marks[kind].add((q, r))
        spec["map"].setdefault(kind, []).append([q, r])

    def spiral(target, radius=26):
        """Hexes near target, nearest first (for placing new things on good ground)."""
        tq, tr = target
        cells = [(tq + dq, tr + dr) for dq in range(-radius, radius + 1)
                 for dr in range(-radius, radius + 1)]
        cells.sort(key=lambda h: (abs(h[0] - tq) + abs(h[1] - tr)
                                  + abs((h[0] - tq) + (h[1] - tr))) / 2)
        return cells

    def nearest(target, want):
        for q, r in spiral(target):
            if terrain_of(q, r) != want:
                continue
            if (q, r) in occupied:
                continue
            if any(abs(q - oq) + abs(r - orr) + abs((q - oq) + (r - orr)) <= 6
                   for oq, orr in occupied):   # keep seats ≥3 hexes apart
                continue
            return (q, r)
        raise SystemExit(f"no free '{want}' hex near {target} — widen the search")

    def add_settlement(sid, name, kind, target, fanzhen, want="plain",
                       hidden=False, scenario=None, road_to=True):
        q, r = nearest(target, want)
        occupied.add((q, r))
        s = {"id": sid, "name": name, "kind": kind, "at": [q, r], "fanzhen": fanzhen}
        if hidden:
            s["hidden"] = True
        if scenario:
            s["scenario"] = scenario
        spec["settlements"].append(s)
        if road_to:                              # pave a spur to the nearest road
            roads = [tuple(c) for c in spec["map"]["road"]]
            if roads:
                near = min(roads, key=lambda h: abs(h[0] - q) + abs(h[1] - r)
                           + abs((h[0] - q) + (h[1] - r)))
                for hq, hr in hex_line((q, r), near):
                    if terrain_of(hq, hr) == "plain" and (hq, hr) not in occupied:
                        add_mark("road", hq, hr)
        return (q, r)

    # ---- 2: the 渤海 coast east of 沧州 (横海军), as the new sea boundary ----
    for r in range(20, 51):
        for q in range(68, 73):
            if terrain_of(q, r) == "plain" and (q, r) not in occupied:
                add_mark("river", q, r)          # sea reads as 大河-blue, impassable

    # ---- 2: new seats filling the roomier interior, + a coastal salt town ----
    add_settlement("wudi", "无棣", "village", (66, 42), "横海军")          # 沧州 coast
    add_settlement("qizhou", "祁州", "town", (28, 24), "义武军")           # 蒲阴, north-centre
    add_settlement("lizhou", "蠡州", "village", (42, 30), "成德军")        # 博野, central plain
    add_settlement("hulugu_lair", "葫芦谷寨", "stronghold", (6, 30), "绿林",
                   want="hills", hidden=True, scenario="gongzhai", road_to=False)
    spec.setdefault("parties", []).append({
        "id": "hulugu_band", "name": "葫芦谷悍匪", "kind": "bandit",
        "home": "hulugu_lair", "speed": 6, "prowl": 4})
    spec.setdefault("labels", []).append({"text": "渤海", "at": [70, 36]})

    # ---- fix the grid extent so every referenced hex sits inside, with margin ----
    def compute_bounds():
        refs = []
        for cells in spec["map"].values():
            refs += [tuple(c) for c in cells]
        refs += [tuple(s["at"]) for s in spec["settlements"]]
        refs += [tuple(s["at"]) for s in spec["sites"]]
        refs += [tuple(lb["at"]) for lb in spec["labels"]]
        refs += [tuple(x["at"]) for x in spec.get("exits", [])]
        max_col = max(q + (r >> 1) for q, r in refs)
        max_row = max(r for q, r in refs)
        min_col = min(q + (r >> 1) for q, r in refs)
        assert min_col >= 0, f"a hex falls off the left edge (min col {min_col})"
        return max_col + 2, max_row + 2     # +1 to include, +1 margin

    # the east edge is fixed FIRST (coast + seats decide it); the estuary then
    # seals right out to that edge per row — so its water can't push the edge
    # outward and open a fresh r6 corridor around its own east end.
    cols, rows = compute_bounds()
    # the 界河/拒马 estuary: the frontier river runs east into the 渤海. Without it
    # the enlarged east plain lets a column flank the 拒马 line and reach occupied
    # 涿州 with no crossing. Seal r7..17 across to the east edge — the western fords
    # stay the only door north, so damming them re-seals 涿州, as 938 left it.
    for r in range(7, 18):
        for q in range(58, cols - (r >> 1)):       # 58 … this row's east edge
            if terrain_of(q, r) == "plain" and (q, r) not in occupied:
                add_mark("river", q, r)

    spec["cols"] = cols                 # FIXED before the estuary — do not recompute
    spec["rows"] = rows
    spec["hexSize"] = HEX_SIZE
    spec["_enlarged"] = True

    with open(HEBEI, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    print(f"enlarged 河北南部 → cols={spec['cols']} rows={spec['rows']} "
          f"hexSize={HEX_SIZE}  ({spec['cols'] * spec['rows']} hexes)")
    print(f"settlements: {len(spec['settlements'])}  parties: {len(spec['parties'])}  "
          f"sites: {len(spec['sites'])}")


if __name__ == "__main__":
    main()
