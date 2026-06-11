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
| `tools/build_standalone.py` | Regenerates the offline standalone HTML from index.html + game.js + scenarios |

## Play the prototype

```bash
cd prototype_web && python3 -m http.server 8765
# open http://localhost:8765/
```

Or just open `prototype_web/shattered_jade_battle.html` — fully standalone,
scenarios embedded, works offline. (It is a build artifact: regenerate with
`python3 tools/build_standalone.py` after touching game.js or scenarios; a test
fails if it drifts. `prototype_web/scenarios` is a symlink to `../scenarios` —
serve from a symlink-aware host, i.e. anything but a Windows checkout.)

Four battles, a difficulty ladder (AI-vs-AI player win rate at 2000 seeds):

| ★ | 劫镖 · 山道伏击 | defend the convoy on the mountain road | 63% |
| --- | --- | --- | --- |
| ★★ | 守桥 · 断后之战 | hold the bridge and ford, 4 vs 9 | 57% |
| ★★★ | 对决 · 黑风三煞 | elite duel around the mound, 3 vs 5 | 48% |
| ★★★★ | 攻寨 · 强袭山寨 | storm the walled mountain village | 41% |

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

Roadmap (see `DESIGN.md` §7.1): M0 ✅ → M1 Godot vertical slice → M2 campaign loop.
