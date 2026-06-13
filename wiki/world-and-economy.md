# World & Economy · 舆图与银钱

## The map
- Regions are `world/<id>.json`, plugged together by border **exits** and listed in `world/realm.json`. Built today: **河北南部** (the pilot, `hebei`), **河南·京畿** (`henan`), plus the **中原** grand-map preview (`zhongyuan`).
- 河北南部 was enlarged (×2 grid + 渤海 coast/estuary + new seats) to **99×81**; `spec.hexSize` draws it large. *(`tools/enlarge_hebei.py`)*
- Terrain & move cost: see [glossary.md](glossary.md) §移动力.

## Settlement buildings (坊) — scaled by size
A settlement's building roster grows **村镇 → 军镇 → 州城**. *(`world.js BUILDINGS`)*

| 坊 | village 村镇 | town 军镇 | city 州城 | What it does |
|---|:--:|:--:|:--:|---|
| **市集** market | ✓ | ✓ | ✓ | Buy 粮草: `2两/day` (village `3`); gouged `+50%` at 恶名≥3. |
| **客栈** inn | ✓ | ✓ | ✓ | Pay `25两` for a rumor that reveals the nearest hidden 寨 **and its band** → posts 攻破 + 剿匪 镖单. |
| **招募** recruit | ✓ | ✓ | ✓ | The candidate pool (see [company.md](company.md)). Shows **available** recruits only. |
| **镖单** jobs | ✓ | ✓ | ✓ | The contract board (see [missions.md](missions.md)). |
| **校场** drill | | ✓ | ✓ | Pay to train the **whole company** once/day, three tiers (more silver → more 经验). |
| **修缮** mend | | ✓ | ✓ | Repair dented 甲械 for `ceil(损/3)两` (founders & hires alike). |
| **铁匠铺** smith | | | ✓ | Raise one member's gear one 品阶 (see prices below). Serves the company, not phantoms. |
| **马行** stable | | | ✓ | Buy 驮马: each `+12` 粮草 capacity, up to 6. |
| **衙门** yamen | | | ✓ | Pay `40两 × 恶名` to wash infamy clean (shown only when 恶名>0). |

## 校场 drill tiers *(`world.js DRILL_TIERS`)*
Once per day, the whole company (every member below max level). Cost scales with heads.

| Tier | 经验 each | cost |
|---|---|---|
| 操演 | +90 | `8 × heads` |
| 操练 | +200 | `16 × heads` |
| 苦练 | +420 | `30 × heads` |

## 铁匠铺 smith prices *(`world.js SMITH_PRICE`)*
Per slot (兵/副/甲/盔), one grade up the 品阶 ladder:

| → grade | 良品 | 精品 | 珍品 | 神品 |
|---|---|---|---|---|
| 两 | 100 | 250 | 600 | 1500 |

## Constants worth knowing *(`world.js`)*
- Start silver `100`; provisions `PROVISION_BASE 6 + CARRY_PER_HEAD 12×heads + 12×驮马`.
- Daily: eat `1×heads`, wage `2×founders + Σ hire wages`.
- 恶名: priced ≥`3`, hunted ≥`6`; atone `40/point`.
- 驮马: `+12` cap each, max `6`, price `80 + 60×n`.

### Add / delete a building
1. Add its key to the right size lists in `BUILDINGS`.
2. Add a `if (has("<key>"))` block in `renderCity` building the panel.
3. Add the `window.ui<Thing>` handler that spends silver and `refresh()`es.
Delete = remove those three. (State it persists, if any, goes in `world` + save/restore.)
