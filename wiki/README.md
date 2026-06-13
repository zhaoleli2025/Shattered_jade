# 碎玉 · Wiki

A single source of truth for **terminology** and **content** (items, units, missions,
buildings…) in *Shattered Jade 碎玉*. One concept per file, one entry per section —
so adding or deleting a thing is a local edit, never a hunt.

> This wiki **describes** what the code does; it is not loaded by the game. When you
> change a number in code, update the matching line here (each page says where the
> data lives so the two stay honest).

## Pages
- [glossary.md](glossary.md) — every in-game term (镖局, 镖单, 品阶, 恶名, 阵亡…).
- [world-and-economy.md](world-and-economy.md) — the map, the silver economy, the 9 settlement 坊.
- [missions.md](missions.md) — the 镖单 board: 押镖 / 攻破 / 剿匪, pay formulas, 劫道.
- [company.md](company.md) — recruits, backgrounds, 特性 traits, 天赋 talents, leveling, permadeath, equipment.
- [combat.md](combat.md) — the six attributes, weapons, armor, 品阶 quality, the five battle scenarios.

## The modular structure — where content lives, and how to add / delete it

The game is **already data-driven where it matters**; the rest is small, well-isolated
tables. To add or remove a thing, touch only the row(s) below:

| To add / delete a… | Edit | Kind |
|---|---|---|
| **Region / overworld map** | new `world/<id>.json` + register in `world/realm.json` | data (JSON) |
| **Battle scenario** (map + fixed deployment) | new `scenarios/<id>.json` | data (JSON) |
| **Settlement on a map** | the `settlements[]` array in `world/<id>.json` | data (JSON) |
| **Roaming party / band** | the `parties[]` array in `world/<id>.json` | data (JSON) |
| **Settlement building (坊)** | `world.js` `BUILDINGS` + a `renderCity` block + a `window.ui*` handler | code |
| **Mission type** | `world.js` `cityJobs()` + the matching branch in `applyBattleResult()` | code |
| **Recruit background** | `world.js` `R_BG` (and `R_NICK`) | code (table) |
| **Trait / 特性** | `world.js` `R_TRAIT` (+ its stat effect in `rcGenerate`) | code (table) |
| **Quality grade / 品阶** | `game.js` `QUALITY` + `world.js` `QUALITY_LADDER` / `QUALITY_LABEL` / `SMITH_PRICE` | code (table) |
| **Weapon / armor / unit template** | `game.js` `rosterTemplates()` / `ARMOR` | code (table) |
| **Founder (核心镖师)** | `world.js` `HERO_BASE` + `HEROES` + `CORE_ROSTER`, and a `P(...)` in `game.js rosterTemplates()` | code (table) |

**The friction line:** everything above the divider is JSON you can drop in without
touching logic; everything that is a *code table* (`R_BG`, `QUALITY`, `rosterTemplates`,
`ARMOR`…) is a flat literal you append to or delete a row from — no control flow to
rewire. If you ever want *full* add/delete-without-code modularity, the next step is to
lift those four tables into `data/*.json` and have `game.js`/`world.js` read them; see
[combat.md](combat.md) §"Going fully data-driven".
