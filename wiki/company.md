# The Company · 镖局成员

The company = the **founders** (核心镖师) + **hires** (部曲). All are *characters* with
six attributes, 特性 traits, and 天赋 talents. Manage them in **校阅** (anywhere).

## Six attributes *(`world.js R_ANAME`)*
血 hp · 武艺 skill · 招架 dfn · 胆识 resolve · 先手 init · 气力 breath. Each grows toward
a cap of `base + GROW.room`; see [combat.md](combat.md) for how they read in battle.

## Founders *(`world.js HERO_BASE` / `CORE_ROSTER`, `game.js rosterTemplates`)*
| id | name | weapon | talents ★ | traits |
|---|---|---|---|---|
| wang | 王铁枪 | 长枪+腰刀 | 武艺★★ | 悍勇, 健壮 |
| liu | 刘三刀 | 腰刀(精品) | 武艺★, 先手★ | 悍勇, 嗜酒 |
| shi | 石敢当 | 大锤 | 血★★ | 天生神力, 铁肺 |
| yan | 燕小乙 | 猎弓+匕首 | 先手★★ | 铁肺, 桀骜 |

## Recruit backgrounds *(`world.js R_BG`)*
Pool of 4 per settlement, reshuffles every `6` days; richer settlements muster better.
`fee` is one-time silver, `wage` is daily upkeep.

| bg | name | fee | wage | leans | typical traits |
|---|---|---|---|---|---|
| tianong | 佃农 | 30–50 | 2 | tanky, cheap | 健壮, 懒惰, 铁肺 |
| tuihuo | 退伙强人 | 40–70 | 3 | hard, wild | 贪婪, 桀骜, 嗜酒, 悍勇 |
| liehu | 猎户 | 70–100 | 4 | archer, fast | 独眼, 铁肺, 悍勇 |
| huanseng | 还俗僧 | 90–130 | 5 | brawny | 天生神力, 嗜酒, 悍勇 |
| tangzishou | 趟子手 | 100–150 | 5 | seasoned | 悍勇, 铁肺 |
| youxia | 游侠 | 200–300 | 8 | elite blade | 天生神力, 悍勇, 跛足 |

Recruits arrive with **hidden** traits/talents — pay the 茶馆 (`max(5, fee/10)`) to reveal
traits, the 医馆 考较 (`max(15, fee/4)`) to reveal ★. Hiring removes them from the board;
they then live only in 校阅. *(rids are unique per place+epoch — no collisions.)*

## 特性 traits & their stat effects *(`world.js R_TRAIT`, applied in `rcGenerate`)*
| trait | effect | | trait | effect |
|---|---|---|---|---|
| 铁肺 tiefei | 气力 +12 | | 健壮 jianzhuang | 血 +6 |
| 悍勇 hanyong | 胆识 +8 | | 桀骜 jieao | 胆识 −4, 武艺 +4 |
| 胆怯 danqie | 胆识 −8 | | 嗜酒 jiujiu | wage +1 |
| 跛足 bozu | 先手 −8 | | 贪婪 tanlan | wage +2 |
| 懒惰 lannuo | 先手 −4 | | 天生神力 shenli / 独眼 duyan | flavour / battle-only |

## 天赋 talents & leveling *(`world.js GROW`, `LEVEL_XP`, `progress`)*
- Levels 1–11. Founders start at **3**. A won battle feeds **280 经验** to the whole roster; 校场 sells 经验 for silver.
- On level-up the 3 most-wanting attributes rise; a **★**-ed attribute grows faster (and rolls higher), so talents shape who a character becomes.

## Equipment *(`world.js world.gear`, slots 兵/副/甲/盔)*
- **Everyone** is equippable — founders **and** hires (a hire's kit is cloned from a background-appropriate donor). The 铁匠铺 serves exactly the fighting company.
- **调拨 (move):** in 校阅, click a member's 装备 chip then another's same slot to swap the 品阶 between them — free, anywhere. Dents/wear stay with the body.
- Gear quality rides into every campaign battle; battle wear (甲 dents) rides home for the 修缮.

## Permadeath (hardcore)
A member **killed** in battle is gone for good — a hire is deleted, a fallen founder is
marked in `world.fallen` and dropped from the roster, wage, and battle line. Flee off the
map edge to *survive* instead. All four founders + all hires dead ⇒ 全军覆没.

### Add / delete a recruit background or trait
- Background: add/remove a row in `R_BG` (and a nickname list in `R_NICK`). The pool weights live in `rcPool`.
- Trait: add/remove a key in `R_TRAIT`; if it changes stats, add its branch in `rcGenerate`.
