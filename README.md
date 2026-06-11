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

## Play the prototype

```bash
cd prototype_web && python3 -m http.server 8765
# open http://localhost:8765/
```

Or just open `prototype_web/shattered_jade_battle.html` — fully standalone,
scenarios embedded, works offline.

Two battles: **劫镖** (defend the convoy on the mountain road) and **攻寨**
(storm the walled mountain village). Left click moves/strikes via the skill bar;
right click inspects anyone; every die roll is public in the combat log.

## Run the sim

```bash
python3 -m pytest sim/tests -q          # the rules, pinned
python3 -m sim.run_batch 500 jiebiao    # AI-vs-AI balance batches (~340 battles/s)
python3 -m sim.run_batch 500 gongzhai
```

The web prototype is the reference implementation; `sim/` is the port and the
balance instrument. Any combat-rule change must land in both.

Roadmap (see `DESIGN.md` §7.1): M0 ✅ → M1 Godot vertical slice → M2 campaign loop.
