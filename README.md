# Shattered Jade（碎玉）

A hardcore turn-based tactical RPG in the spirit of **Battle Brothers**, set in a
grounded wuxia world modeled on the Five Dynasties (五代, c. 907–960). You lead a
mercenary escort company — 镖局 — through a fractured realm building toward the
Khitan invasion. Every blade has a name; permadeath is permanent: 宁为玉碎，不为瓦全.

## What's here

| Path | What it is |
| --- | --- |
| `DESIGN.md` | The design document — source of truth, full versioned changelog |
| `RESEARCH.md` | Nine consolidated Battle Brothers research digests (the quantitative rules reference) |
| `scenarios/*.json` | Battles as data — read by both the web prototype and the sim |
| `prototype_web/` | Playable browser battle prototype (no build step) |
| `sim/` | M0: the engine-agnostic Python combat sim — same rules, pytest-locked, with an AI-vs-AI batch runner |
| `world/*.json` | Overworld regions as data (M2 track) — hex strategic map, first region: 河北南部 |
| `godot/` | M1: the Godot 4 client — GDScript sim-core port, pinned to Python golden vectors |
| `releases/` | Frozen STABLE editions of the standalone HTML (test-gated, version-stamped) |
| `tools/build_standalone.py` | Regenerates the offline standalone HTML from index.html + game.js + scenarios |

## Play the prototype

```bash
python3 tools/serve.py            # dev server, Cache-Control: no-store —
# open http://<host>:8023/        # every refresh is fresh, no cache roulette
```

For a **stable edition**, don't play the dev tree — cut a release:

```bash
python3 tools/release.py          # gate: full suite green → stamps the DESIGN.md
                                  # version into releases/shattered_jade_vX.Y.html
```

Each release is a single offline file (scenarios embedded) you can copy anywhere
and double-click; `releases/latest.html` always points at the newest. The dev
artifact `prototype_web/shattered_jade_battle.html` is rebuilt by
`python3 tools/build_standalone.py` after touching game.js or scenarios; a test
fails if it drifts. (`prototype_web/scenarios` is a symlink to `../scenarios` —
serve from a symlink-aware host, i.e. anything but a Windows checkout.)

Five battles, a difficulty ladder (AI-vs-AI player win rate, 300 seeds, v0.25):

| ★ | 劫镖 · 山道伏击 | defend the convoy on the mountain road | 60% |
| --- | --- | --- | --- |
| ★★ | 守桥 · 断后之战 | hold the bridge and ford, 4 vs 9 | 56% |
| ★★★ | 对决 · 黑风三煞 | elite duel around the mound, 3 vs 5 | 47% |
| ★★★★ | 攻寨 · 强袭山寨 | storm the walled mountain village, 6 vs 8 | 51% |
| ★★★★★ | 血战 · 拒马河 | endgame: the Khitan column at the river line, iron vs iron, 12 vs 12 on 17×11 | 51% |

Left click moves/strikes via the skill bar; right click inspects anyone; every
die roll is public in the combat log.

## Run the sim

Requires **Python 3.10+** for pytest/batches (the package itself imports on 3.9).

```bash
python3 -m pytest -q                       # the rules, pinned (76 tests)
python3 -m sim.run_batch 500 jiebiao       # AI-vs-AI balance batches (~340 battles/s)
python3 -m sim.run_batch 500 gongzhai      # also: shouqiao, duijue
```

The web prototype is the reference implementation; `sim/` is the port and the
balance instrument. Any combat-rule change must land in both (and the standalone
gets rebuilt — see above).

## Overworld (M2 track, headless v0)

The strategic layer uses the same hex grid as battles, M&B-style on a FIXED
historical map: mountain ranges are walls pierced by named passes, rivers
cross at named fords, and battle scenarios are anchored to real places (caught
at 滹沱桥 → 守桥; at a 拒马 ford → 血战; 虎牢关 is always the duel). The BB
living-world layer runs on top: roaming parties intercept on contact, hidden
lairs are found by proximity, provisions burn daily.

**Play it in the browser** — `python3 tools/serve.py`, open `/world.html`:
click-to-travel with day estimates, camp, encounters whose 「开战」 button
drops you into the battle page with the right scenario.

The realm is **modular** (`world/realm.json`): 河北南部 (`hebei.json`) is the
pilot area; 河南·京畿 is built; 河东·关中·西北·山东·淮南·荆楚·剑南·幽云 are
registered sockets — author one JSON in the same pattern, link the exits, and
the realm grows. `world/zhongyuan.json` (56×36, 27 settlements) is the composed
grand-map preview of the whole.

```python
from sim.overworld import load_world, travel, render
w = load_world("hebei", seed=0)   # or "zhongyuan" for the grand map
travel(w, "dingzhou")     # 镇州 → 定州 along the 官道: 2 天 (unless intercepted)
print(render(w))          # ASCII map: 镖=you 匪=bandits 商=caravan 巡=patrol 骑=Khitan
```

## M1 — the Godot client (in progress)

The stable ultimate edition is the Godot 4 desktop game (`DESIGN.md` §7). The
GDScript sim-core port lives in `godot/sim_core/`, pinned bit-for-bit to the
Python sim by golden vectors (floats travel as IEEE-754 bits — JSON text loses
the 17th digit):

```bash
python3 tools/export_golden.py    # regenerate vectors after sim-core changes
/data/zhaoleli/opt/godot/godot --headless --path godot --script tests/run_tests.gd
```

This server runs **Godot 4.1.4** (`/data/zhaoleli/opt/godot/godot` — glibc 2.27
caps us there; 4.2+ needs 2.28). Develop/play the scenes on a desktop with any
Godot 4.x — the headless parity suite is the contract between the two.

Roadmap (see `DESIGN.md` §7.1): M0 ✅ → M1 Godot vertical slice (started) → M2
campaign loop.
