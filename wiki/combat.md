# Combat · 战斗 (items & scenarios)

Battles are hex tactics with **public dice**. Hit% = `武艺 − 对方招架 + 准头(weapon acc)
+ 高地 + 围攻`, clamped **5–95**. Damage chips **armor** first (an ablative pool), then 血.
气力 (breath) is the per-action stamina that everything strapped on (坠气 `br_tax`) drains.

## Weapons *(`game.js rosterTemplates()`; quality buys numbers, family buys the special)*
| weapon | hands | reach/range | dmg | vs armor | special |
|---|:--:|---|---|---|---|
| 长枪 spear | 2 | reach 2 | 22–32 | 0.9 | 枪林 spearwall (brace) |
| 短矛 short spear | 1 | — | 16–24 | 0.9 | 枪阵 spearwall |
| 腰刀 / 砍刀 saber | 1 | melee | 18–26 / 17–26 | 1.0 | 斩首 decap, 流血 bleed |
| 九环刀 ring-saber | 1 | melee | 24–34 | 1.0 | 斩首 decap, bleed *(leaders)* |
| 大锤 maul | 2 | melee | 28–40 | **2.0** | 碎甲 demolish (×3 armor) |
| 大斧 axe | 2 | melee | 30–44 | 1.3 | 横扫 sweep, 劈砍 chop |
| 戟 halberd | 2 | reach 2 | 22–32 | 1.0 | 横扫 sweep |
| 大关刀 guandao | 2 | melee | 28–42 | 1.2 | 横扫 sweep, chop, bleed |
| 九节鞭 chain-whip | 1 | melee | 18–28 | 0.9 | 兜头 headhunt, **ignores shield** |
| 猎弓 bow | 2 | range 7 | 14–24 | 0.6 | 瞄准 aimed |
| 弩 crossbow | 2 | range 6 | 22–32 | 0.8 | 瞄准 aimed, pierce 0.5 |
| 匕首 dagger | 1 | melee | 14–22 | 0.0 | pierce 1.0, no-head |
| 短刀 short blade | 1 | melee | 14–22 | 0.8 | — |

## Armor & helmets *(`game.js ARMOR`)* — protection / 坠气(br_tax)
| body 甲 | protect | br_tax | | head 盔 | protect | br_tax |
|---|---|---|---|---|---|---|
| 无甲 | 0 | 0 | | 无盔 | 0 | 0 |
| 布甲 | 25 | 3 | | 布帽 | 15 | 1 |
| 皮甲 | 60 | 8 | | 皮盔 | 40 | 3 |
| 铁甲 | 110 | 16 | | 铁盔 | 80 | 7 |

## 品阶 quality grades *(`game.js QUALITY`)*
A multiplier laid over any weapon/armor. The smith climbs it one step at a time.
| grade | dmg× | acc+ | protect× | br_tax× |
|---|---|---|---|---|
| 凡品 fan | 1.00 | 0 | 1.00 | 1.00 |
| 良品 liang | 1.10 | +2 | 1.15 | 1.00 |
| 精品 jing | 1.20 | +4 | 1.30 | 0.95 |
| 珍品 zhen | 1.35 | +7 | 1.50 | 0.90 |
| 神品 shen | 1.50 | +10 | 1.75 | 0.85 |

## Battle scenarios *(`scenarios/*.json`)*
The overworld picks one from the hex's terrain (or an anchored 关/陉/桥/渡, or a 寨's own).
| id | name | shape |
|---|---|---|
| `jiebiao` | 劫镖 · 山道伏击 | convoy ambush on the 官道 |
| `shouqiao` | 守桥 · 断后之战 | hold a bridge / 渡 |
| `duijue` | 对决 · 黑风三煞 | a small duel on open ground |
| `gongzhai` | 攻寨 · 强袭山寨 | storm a 山寨 (walls) |
| `juma` | 血战 · 拒马河 | the 契丹 column at the frontier |

## Factions (the randomized warbands a **campaign** fight draws from) *(`game.js ENEMY_POOLS`)*
- **绿林 bandits** — 喽啰/独眼龙/二麻子/笑面虎/蛇矛子/钻山豹… led by 坐山雕 or 过山风.
- **契丹 Khitan** — 皮室 iron guard, 射雕手 archers, 汉军 spear/crossbow auxiliaries, led by 耶律详稳.

A campaign battle fields **your actual company** (3–4 founders + hires, with their levels &
gear) vs a randomized warband scaled to it (≤1 leader), seeded per encounter. The fixed
`scenarios/*.json` deployments stay deterministic — they are the test fixtures.

---
### Going fully data-driven (optional next step)
Today four tables are code literals: `rosterTemplates()` & `ARMOR`/`QUALITY` (`game.js`),
`R_BG` & `R_TRAIT` (`world.js`). To make units/items/backgrounds add-or-delete *without
touching code*, lift each into a `data/*.json` file and have boot `fetch()` it (the
scenario/world loaders already show the pattern). Then this wiki's tables and the game read
the **same** source. Until then, they're flat literals — appending or deleting a row is safe
and local.
