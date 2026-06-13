# Glossary · 名词

Terminology, alphabetised by pinyin. Each entry is self-contained — add or remove one
without touching the others. *(code anchor)* points at where the term is implemented.

- **镖局 / the bureau** — the player's company: the founding **镖师** plus hired **部曲**.
- **镖师 (founder)** — one of the four founding hands (王铁枪 / 刘三刀 / 石敢当 / 燕小乙). They earn levels in the field. *(`world.js CORE_ROSTER`, `HERO_BASE`)*
- **部曲 (hire)** — a recruited member. Fights, eats, draws a wage, can be drilled & equipped, can die. *(`world.js world.members`)*
- **镖单 (contract)** — a job taken from a settlement board. One at a time. See [missions.md](missions.md).
- **粮草 (provisions)** — food, in day-units. Burns `1 × headcount` per day; capacity = `6 + 12×heads + 12×驮马`. Empty ⇒ the company starves. *(`world.js capacity/dailyFood`)*
- **移动力 (move points)** — terrain cost per hex; `8`/day. 官道 1, 旷野/渡 2, 丘林 3, 苇荡 4; 大河·层峦 impassable. *(`world.js COST`, `MOVE_PER_DAY`)*
- **银两 (silver)** — currency. Start `100`. Earned from 镖单; spent on 粮草, 招募, 校场, 铁匠铺, 马行, 衙门. *(`world.js GOLD_START`)*
- **饷 (wage)** — daily upkeep, paid at dawn: `2 × founders + Σ hire wages`. Unpaid ⇒ morale wavers. *(`world.js dailyWage`)*
- **恶名 (infamy)** — earned by 劫道 (banditry). `≥3` ⇒ markets gouge & the board thins; `≥6` ⇒ a 海捕 writ and 缉捕官军 hunt you. Wash it at the 衙门 (`40 / point`). *(`world.js INFAMY_PRICED/HUNTED/ATONE_RATE`)*
- **品阶 (quality grade)** — the fineness ladder on a piece of gear: 凡品→良品→精品→珍品→神品. Quality buys numbers (dmg/acc/protect); *family* buys verbs (the special). See [combat.md](combat.md). *(`game.js QUALITY`)*
- **特性 (trait)** — an innate quirk (悍勇, 铁肺, 天生神力, 嗜酒…), with a stat effect baked in at generation. Founders have them too. See [company.md](company.md). *(`world.js R_TRAIT`)*
- **天赋 (talent / ★)** — a starred attribute that grows faster on level-up (1–3★). Shown as ★ in 校阅. *(`world.js GROW`, `starsOf`)*
- **校阅 (muster)** — the roving roster panel (header「校阅」, openable anywhere): one list of every member with stats, traits, talents, gear. Click a name for the full sheet; click 装备 chips to 调拨. *(`world.js renderMuster`)*
- **调拨 (transfer)** — move a gear slot's grade between two members. Free, anywhere. *(`world.js uiGearChip`)*
- **斥候 / 视野 (sight)** — reveal range: 3 hexes (+1 ending on a hill). Spots roaming parties & hidden 寨. *(`world.js SIGHT`)*
- **贼巢 / 山寨 (lair / stronghold)** — a hidden bandit den; revealed by sight or 客栈 intel; razed for a 攻破 bounty (disbands its band). *(`world.json settlements kind:"stronghold"`)*
- **劫道 (waylay)** — turn bandit yourself: ambush a 商队/巡骑 for loot + 恶名. *(`world.js offerWaylay`)*
- **扎营 (camp)** — hold position one day (burns 粮草 & 饷; lets a patrol pass). *(`world.js doCamp`)*
- **阵亡 (killed) / hardcore permadeath** — a member who *dies* in battle (not one who flees off-edge) is struck from the roster **forever** — hires vanish, fallen founders go to `world.fallen`. Whole company dead ⇒ 全军覆没 (重开). *(`world.js applyBattleResult` fallen-loop, `livingCore`)*
- **截击 / encounter** — a hostile within reach halts the march and offers 开战/脱离; the hex's terrain (or an anchored 关/陉/渡) picks the battle scenario. *(`world.js emitEncounter`)*
