# Shattered Jade (碎玉) — Design Document v0.30

> **Title: Shattered Jade (碎玉)** — final, 2026-06-11. 宁为玉碎，不为瓦全 ("better
> shattered jade than intact tile"): the permadeath creed in two characters — your
> people die whole, or live broken. Earlier working titles: 血与银, 玉与天命, 碎玉行.
>
> Lore anchor: the **传国玉玺** — the jade Seal of the Realm, the physical Mandate of
> Heaven — vanished historically in **937**, burned with the last Later Tang emperor
> when the Khitan-backed coup took Luoyang: this game's exact crisis. The realm's own
> jade, shattered in our era (legendary-artifact hook, F4).
>
> A hardcore turn-based tactical RPG in the mold of **Battle Brothers**, reskinned and
> re-grounded in a **wuxia setting modeled on the Five Dynasties (五代, c. 907–960)** —
> the fractured age between Tang and Song — with the community's best-documented pain
> points fixed from day one, and **the Khitan (Liao) invasion as every campaign's
> essential climax**.
>
> Design stance: **faithful to the proven skeleton, differentiate via QoL + setting.**
> Numbers below start from Battle Brothers' shipped values — known-good *for BB's exact
> system mix*; wherever we change an input (XP sources, info reveal, scaling), the
> dependent numbers must be re-verified in batch simulation (see §7.1 M0).
>
> Companion material: `RESEARCH.md` (the nine Battle Brothers research digests,
> consolidated — the wiki digests are M0's quantitative rules reference). A 53-finding
> adversarial design review was incorporated at v0.2; its substance lives in the §10
> changelog.

---

## 1. Vision

You lead a **free company of hired blades** in a fractured age: the great dynasty has
fallen, courts rise and fall in a decade, and the roads belong to whoever can hold
them. What the company *is* depends on its origin (§5.9): in the default start you are
the **chief escort master (总镖头)** of a struggling **escort bureau (镖局)** — but you
can instead lead a **broken garrison company selling its spears to the warlord courts**
(the soldier's path: military contracts, pitched battles, siege work), a lone
swordsman's following, or post-v1 origins (smugglers gone straight, lay monks, a
performing troupe). Whatever the banner, the frame is constant: **you are never on the
field.** NPCs address you, contracts carry your name, rivals challenge you — but your
people walk the roads and fight in your stead, as real senior masters did. You take
contracts: guard a tea caravan through bandit country, clear a mountain stronghold,
stand as paid spears in a jiedushi's battle line, escort a magistrate's coffin home.
Your people are farmhands, ex-bandits, defrocked monks, performers. They have names,
pasts, hidden talents, and they die. Permanently. The company survives them.

**One-line pitch:** *Battle Brothers in the jianghu — Water Margin's outlaw China, where
every blade has a name and a grave.*

**Tone references:** 《水浒传》 Water Margin · **《刺客聂隐娘》 The Assassin** (the
Tang jiedushi world this game inherits — restraint, texture, institutional decay) ·
Xu Haofeng's grounded martial-world films 《师父》/《倭寇的踪迹》/《箭士柳白猿》 ·
老舍《断魂枪》 (a dying escort-master in a world that no longer needs him — this game's
theme in 8 pages) · 王度庐's Crane-Iron novels · 《大明劫》 (for its plague-and-collapse
tone, era aside). NOT xianxia: no flying, no energy blasts, no cultivation realms.
Martial arts are *skill*, slightly larger than life at the very top. The supernatural
exists only at the edges of the world — mirroring Battle Brothers' asymmetry: **humans
stay grounded; monsters carry the exotic.**

### 1.1 The five pillars (non-negotiable, they require each other)

1. **The company is the protagonist.** No player avatar *on the field* (the company's
   unseen master — 总镖头, captain, chief, by origin — exists in fiction only).
   Individual fighters are expendable; the company is resilient. Losing your best blade
   is a tragedy; losing a battle is a setback; only losing the company ends the run. **Corollary: no mechanic may punish the player *for* being in a
   weakened state** — the world scales on time and distance, never inversely on player
   stumbles (see §5.7).
2. **Attachment engine.** Procedural identity — backgrounds, hidden traits, talent stars,
   permanent scars, sworn brotherhoods, background-keyed events — makes every recruit a
   potential story. Money must never be able to buy away all the uncertainty (§4.3).
3. **Bounded, legible RNG.** One readable hit formula, clamped 5–95%. Crits are spatial
   (head hits) and answered by buying a helmet. Everything beatable with the right
   strategy from day one. **Transparency principle (governs F1): combat math is always
   exact and fully logged; social reads on the strategic layer may be fuzzy, but are
   always signaled as such** (a client's patience shows as a facial state, not a number).
4. **Weapons are tools, not stat sticks.** Every weapon family answers a different
   defensive layer (shields, armor, HP, stamina, morale). Armor is ablative pools per
   body part. "Best weapon" is always matchup-dependent.
5. **Economy is pressure, not profit.** Exponential wages, decaying fame, spoiling food,
   gear durability. Breaking even is OK. The treadmill is the narrative. **M2 tuning
   KPI: a median-skill company at default difficulty oscillates within ±15% of
   break-even through day 40, with at least two forced liquidity crunches.**

### 1.2 What we fix (the differentiator list)

Sourced from community/mod demand and the devs' own postmortems (`RESEARCH.md`). Each
fix was adversarially reviewed for second-order damage; the versions below are
post-review (findings summarized in the §10 v0.2 entry).

| # | Battle Brothers pain point | Our fix (v0.2) |
| --- | --- | --- |
| F1 | Opaque math ("Roll fail (dice 90)"), hidden morale checks | **Combat transparency**: full modifier breakdown on hit tooltips and log; morale checks logged *after resolution* with trigger, base Nerve, every modifier, the roll, and resulting state. Strategic-layer social reads are fuzzy-but-signaled (pillar 3). Delivered incrementally: M1 = hit tooltip + plain log; rich log & settlement numbers by M3 |
| F2 | No save during 30-minute battles | **Suspend save** (save-on-exit, deleted on resume). Ships M3/M4 when the command-log replay infra makes it nearly free; M2 has overworld saves only |
| F3 | Brutal early game | **Gentler days 1–15**: starter contracts capped in difficulty, no difficulty-twists in the window, one guaranteed-fair early fight chain; full cruelty after |
| F4 | Late-game dead zone | **Endgame ladder with player-side fuel**: elite contracts and crisis rewards drop **famed gear** (randomized superior stats) and **secret manuals** (true chase upgrades, hard cap 1 manual per escort); 2–3 fixed **legendary sites** (a sword-grave, a haunted monastery — and rumors of the **lost Seal of the Realm 传国玉玺**, vanished 937: the ultimate famed artifact and the title's namesake); the rival bureau as climax. Enemy scaling has a stated ceiling calibrated (in batch sim) to a plateaued 12-man veteran company |
| F5 | Contracts samey | **Twist tables, two kinds**: *flavor twists* (weather, cargo-is-a-person, moral fork) at ~35%; *difficulty twists* (ambush, betrayal, client lied) at a lower rate, lie bounded to +1 skull, per-N-contracts cooldown, **never in days 1–15**. Rival-bureau twists capped per campaign arc so each lands |
| F6 | Blind recruitment feels like artificial difficulty | **Graduated information, capped**: free look = background + 1 hint; teahouse gossip (~10% of hire cost) = traits; physician exam (scales with background price) = talent *count* + range of *one player-chosen* attribute. **The full star map is never purchasable** — stars reveal themselves through level-ups (pillar 2). |
| F7 | Crises play like normal contracts, gold-only rewards | Crisis contracts get **unique mechanics** (siege ladders, fire arrows, civilians to evacuate) and **non-monetary rewards** (titles, famed gear, ending slides that reference your deeds) |
| F8 | Forced slow pacing | Separate speed sliders (map / combat animation) + instant-resolve toggle for trivial fights (free via sim/view separation) |
| F9 | Non-combat contracts give no XP | Non-combat contracts award **fame and relations** (not character XP — XP stays combat-fed so the roster-strength and wage curves keep their calibration) |
| F10 | Goals silently auto-complete without reward (snapshot bug) | Goal eligibility evaluated **continuously**; retroactive credit |
| F11 | Morality stat tracked but vestigial | **Xia (侠义)** does real work at the extremes (high: folk discounts, righteous branches, militia aid; low: black market, underworld contracts). **The middle is "no perks," never penalized**; Xia drifts slowly toward 50, so maintaining an extreme is the cost. Some moral forks pay in fame/loot instead of Xia, so dilemmas stay dilemmas (start: 50) |
| F12 | No downtime texture | **Camp roles, not base-building**: when camped — sparring (small *stat-roll* training, no XP), physician treatment, bonus-rate repairs, cook. Camp roles consciously replace BB's retinue followers. Camp days consume extra provisions (a drain to balance the relief) |
| F13 | Clunky inventory; paper-notepad gear comparison (PC Gamer's verdict-capping complaint) | **Comparison UX native**: side-by-side item compare vs any equipped escort, roster-wide equipment grid, favoriting/sell-protection, full keybinds. Comparison tooltips are in the M1 bar |
| F14 | Zero tutorials ("40 minutes of YouTube before I'm ready to play") | **Contextual onboarding**: first-time popups for ZoC, Breath, formation editor, loot-repair-resell; the F3 guaranteed-fair fight chain doubles as the teacher. Owned by M1/M2 deliverables |

---

## 2. Setting

### 2.1 World

> 「天子，宁有种邪？兵强马壮者为之尔。」
> *"A Son of Heaven? Is one born to it? Whoever has the strongest troops and horses —
> that is all."* — 安重荣, 《新五代史》. The era's creed, and the game's.

An unnamed fractured realm modeled on the **Five Dynasties (五代, c. 907–960)**: the
great dynasty has fallen, the throne changes hands every decade, and real power sits
with **three rival military provinces (藩镇), each under a military commissioner
(节度使)** — the procedural "noble houses." It is the perfect mercenary era: loyalty is
a commodity, governors' own guard corps (牙兵) mutiny and murder their masters, armies
are bought and sold — and nobody polices the roads, which is why escort bureaus exist.
(The formal 镖局 is historically a Ming–Qing institution; backdating it is standard
wuxia convention — 杨家将 backdates worse — and we state the anachronism honestly.)

Beyond the northern passes, the steppe has been united under the **Khitan Empire
(契丹 / the Liao 辽)** — a young, organized, expansionist power, not a faceless horde
(§2.2). The frontier prefectures — **the Northern Marches** (边州, modeled on the
燕云十六州) — are the dangerous edge of the map: horse smuggling, captive ransom,
refugee columns, and the foothold the invasion will use when it comes (§2.3).

- **Geography == BB terrain table**: plains / forest (bamboo, pine) / marsh (rice paddy,
  salt marsh) / hills / mountains / snow (the Marches) / rivers as roads-with-boats.
- **The jianghu** (江湖, "rivers and lakes") is the social layer: the world of those who
  live outside the court's order — escorts, outlaws, sects, beggars, smugglers. Your
  bureau lives here.
- **Era texture**: Shatuo Turk generals founded half the era's "Chinese" dynasties
  (李克用/李存勖, 石敬瑭, 刘知远) — ethnicity lines were blurry and armies mixed, which
  the game reflects; adopted-son corps (义儿军 — 李克用's adopted sons live on in legend
  as the 十三太保) organized loyalty by oath, which §4.4's sworn brotherhood echoes;
  imperial exams limped on (the failed scholar background survives); money is copper
  cash (文/贯) with silk bolts and silver ingots for large payments.

**Reference shelf (for events, contracts, and flavor writing):**
*History*: 《新五代史》/《旧五代史》 · 《资治通鉴》 (Five Dynasties chapters) · 欧阳修
《伶官传序》 (performers given rank — the era's decadence in one essay). *Key real events
to mine*: 907 the fall (朱温); 916 Abaoji unites the Khitan; **936 石敬瑭 cedes the
Sixteen Prefectures for Khitan cavalry and calls himself the "child emperor" (儿皇帝)**
— the template for our collaborator-jiedushi arc; **946–947 the Khitan take the capital,
their 打草谷 foraging columns strip the countryside, and popular fury drives them back
north** — the template for our invasion crisis and its winnable ending. *Genre fiction*:
《残唐五代史演义》 · 《十三太保》 (李存孝!) · 杨家将 sagas (the canonical Liao-war
melodrama, one era later) · 《天龙八部》's 萧峰 (the sympathetic-Khitan precedent).
*Film*: 《刺客聂隐娘》 (visual north star) · 《满城尽带黄金甲》 (Five Dynasties court
opulence, for the rare palace contract).

### 2.2 Factions & enemies (asymmetric design — each attacks a different player system)

| Faction | BB analog | Their gimmick (counterplay target) |
| --- | --- | --- |
| **Mountain bandits / river pirates** (山贼/水匪) | Brigands | Mirror humans — the readable baseline; loot is their gear |
| **Deserter soldiers** (溃兵) | Deserters | Well-armored, disciplined formations — armor-cracking test |
| **The Khitan Empire** (契丹/辽) | Orcs (the mounted threat) | A rival *state*, not a horde: disciplined cavalry — horse+rider as one unit, Charge displaces your line, mounted archers kite, horse killed → rider fights on, diminished — flanked by Han auxiliary spear-and-crossbow infantry, plus 打草谷 foraging columns plundering the countryside. Counter: terrain choice, spearwall (枪 — the historically correct answer), night, walls. *Enters with the invasion crisis; v1 ships a scoped composition (§7.1 M4)* |
| **The Pure Lotus Teaching** (净莲教, fictional sect — gloss 妖教, never 邪教) | Cultists + Undead | Rank-and-file are starving peasants drawn by famine relief — the grimness aims at desperation. Fanatic morale (never routs), poison, fire; only the priest caste touches the corpse-arts (attacks: fatigue & morale). *Post-v1 with its crisis* |
| **The Restless Dead** (僵尸/鬼) | Undead | Jiangshi feel no fatigue, never check morale; fallen men rise; ghosts (鬼) attack Nerve directly — herded by corpse-drivers (赶尸人, the necromancer analog). Regionally concentrated; spoken of in rumor ("they say the dead walk in Hedong") — the supernatural stays at the edge you're forced to travel toward |
| **Beasts & yaoguai** (虎/狼/妖) | Beasts | Tigers, giant serpents (poison), fox spirits (illusion/charm) — *charm/illusion post-v1* |

Design rule (adapted for the historical invasion): the grimness aims at **war, banditry,
and desperation — never at peoples**. The Khitan are portrayed as 杨家将 and 天龙八部
portray them: a real, organized empire with political goals, Han officials and auxiliary
troops, collaborator jiedushi on the southern side of the ledger — and sympathetic
individuals (the **契丹逃卒** recruit background is our 萧峰 nod). The era itself refutes
clean Han-vs-nomad framing: half its southern dynasties were Shatuo-founded (§2.1).
Religious enemies stay fictionalized (Pure Lotus, as Jin Yong fictionalized 明教).

### 2.3 Late-game crises — one essential, plus variable

**The essential climax — The Khitan Invasion (契丹南下).** Every campaign builds toward
it; it is the fixed backbone that gives each procedural run an arc (and answers the
"macro-narratives vary little" criticism of BB head-on). Structure, mined from 936–947:

- **Foreshadowing (from ~day 50)**: border situations in the Marches — refugee columns,
  horse prices spike, captive-ransom and scout-the-passes contracts appear, teahouse
  rumors name the Khitan emperor.
- **The trigger — the collaborator's gambit (the 石敬瑭 template)**: one of the three
  jiedushi invites the Khitan in, ceding the Northern Marches for cavalry support and
  styling himself the "child emperor" — civil war and invasion merge into one crisis.
- **The crisis (day ~80–100, 30–100 days)**: 打草谷 foraging columns plunder villages
  (settlement situations), walled cities fall under siege (F7 unique mechanics: ladders,
  fire arrows, civilians to evacuate). Contracts on all sides: loyalist relief,
  evacuation, and scouting; collaborator escort work (Xia cost); even Khitan-paid
  caravan protection — silver is silver (deep Xia cost, southern relations damage).
- **Resolutions (F7 — the ending slides remember which)**: the passes held; a decisive
  field battle; or a negotiated tribute peace. Historical precedent makes the "win"
  honest: the real 947 occupation collapsed under its own plundering — a world where
  ordinary people's fury (and companies like yours) can actually push the invader back.

**Variable secondary crises** (0–1 per campaign, firing *before* the invasion — both
post-v1):

1. **War of the Provinces** (藩镇混战) — threatens *access*: roads close, river traffic
   stops, pick a side or starve neutral.
2. **The Pure Lotus Rising** — threatens *existence*: the sect's human armies
   front-stage, jiangshi as the priests' escalation; plague-villages fall; settlements
   can be permanently lost (opt-in "permanent destruction" setting).

Telegraphed ~day 50–70, begins day 80–100, gated on company readiness. **v1 ships the
essential Khitan Invasion; the two variable crises are post-v1.**

---

## 3. Tactical combat

Hex grid, individual initiative (not team turns), 12 fielded default (engine supports
18). Battlefield generated from the overworld tile. Deployment phase with saved default
formations — surfaced by onboarding (F14), not buried. *(Harness rule, not a combat
rule: headless batches — sim `engine.py` — terminate an undecided battle as a draw at
round 100 so AI-vs-AI runs always halt; most battles end well under 30 rounds, but
守桥's rout-and-rally chokepoint grinds to the cap in ~0.7% of seeds — those score
as draws. The prototype has no cap.)*

### 3.1 Action economy — two stacked resources

- **AP**: 9 per turn, full refresh. Move 2 AP flat or road / 3 rough / 4 paddy-water;
  +1 per level climbed (uphill only — both implementations charge nothing downhill;
  wording fixed v0.21). Most 1H attacks 4 AP; heavy 2H attacks 6 AP. *(M0 terrain:
  flat/road 2 AP, forest 3; the implemented `water` is 守桥's impassable river —
  nobody enters it. The wade-through 4-AP paddy and its ×0.75 melee multiplier
  (§3.3 M3) are future terrain.)*
- **Switching weapons** (to a bagged sidearm) costs **4 AP** — the pinned archer's
  dagger, the spearman's backup saber. A Quick-Hands-style technique makes the first
  swap each turn free (later).
- **Roads (官道/山道)** on the battlefield: normal AP, but **half Breath per hex (1 vs
  2)** — fresh legs on good ground. Battles triggered on escort routes seed the road
  across the tactical map, so the convoy fights best along its own artery — and
  ambushers must spend stamina coming down to it. (Roads also speed overworld travel,
  §5.1 — same artery, both layers.)
- **Breath (气力)** — a **depleting pool** (display flipped from BB's accumulating
  fatigue; identical math, reads naturally in both languages: 气力用尽 = can't act).
  Start full; every action drains it; recover 15/turn; at zero you can neither move nor
  strike. Being struck drains extra (−5 baseline; a weapon's declared drain **replaces**
  it, never stacks — 大锤 drains 20 total, not 25). Jiangshi never tire.
- **坠气 (the carry tax)** — everything an escort straps on drags on his wind. Every
  equipped item — armor, helmet, weapon, the bagged sidearm (and shields, when they
  land) — declares a 坠气 value, and **max Breath = base − total 坠气**: BB's
  carry-fatigue made diegetic. The sidearm's tax is paid all battle, sheathed or drawn;
  换械 swaps the verbs, never the math. 坠气 is deliberately distinct from the
  per-strike 气力 cost — one is what you carry, the other is what you spend.
- **Initiative** = base − Breath spent − 坠气 penalty, recomputed each round, highest
  first. *(M0 implements base − Breath spent only; the explicit 坠气 term is deferred
  to M1 — 坠气 already taxes max Breath, so heavies still slide as they tire.)*
  Implemented timing, both engines: the queue is sorted **once at round start, before
  any upkeep** (the +15 recovery never reorders the round in progress); ties keep
  scenario unit order (stable sort) — load-bearing for JS replay parity.
  The 轻功 *Lightness* technique converts current initiative into defense — so
  exhaustion erodes exactly the builds that depend on speed.

### 3.2 Damage model — two-layer, per-body-part

Three pools per man: **Head armor / Body armor / Hitpoints**. Each weapon has two knobs:

- `%armor_eff` — how hard it chews armor (hammers high)
- `%armor_pierce` — how much damage bypasses armor entirely (daggers, crossbows high)

Per hit: armor damage = dmg × %armor_eff; bleed-through HP = dmg × %armor_pierce − 10% of
remaining armor on the struck part; overflow when armor breaks. **Head hits are the crit
system**: 25% base, ×1.5 HP damage, routed to the helmet pool. Meteor hammers and
nine-section whips hunt heads (+10/15%); the 铁头功 *Iron Skull* technique negates bonus
head damage.

**Armor tiers (v0.17, live in demo + sim)** — protection is bought with 坠气, and 坠气
is paid in max Breath (气力上限 = 体格底子 − 甲坠 − 盔坠 − 兵坠 − 副兵坠, §3.1), the
BB trade-off:

| Tier | Body 甲 | Helmet 盔 |
| --- | --- | --- |
| Light 布 (cloth) | 布甲 护 25 · 坠气 3 | 布帽 护 15 · 坠气 1 |
| Medium 皮 (leather) | 皮甲 护 60 · 坠气 8 | 皮盔 护 40 · 坠气 3 |
| Heavy 铁 (iron) | 铁甲 护 110 · 坠气 16 | 铁盔 护 80 · 坠气 7 |

A full iron loadout costs 23 Breath off the cap before the weapon's own 坠气 (§3.10) —
石敢当 in iron with the great maul opens at 64 of 93. The iron man starts every battle
a quarter of his stamina poorer than the runner, and slides down the initiative order
as he tires. Tier numbers are 凡品 base values — quality grades (§3.11) scale
protection up and 坠气 down from here. (Iron helms will additionally cost Vision when
that rule lands, M2; named armors like 山文甲 are 神品-grade pieces, §3.11.)

### 3.3 Hit formula (fully surfaced in UI)

```text
chance = attacker_skill − defender_defense
       + situational adds (height ±10/level, surround +5/extra attacker,
         skill accuracy, shieldwall …)
       × state multipliers (morale ×1.1/0.9/0.8/0.7, night ×0.7 ranged,
         paddy ×0.75 melee, injuries …)
clamped 5–95.  Defense above 50 counts half (soft cap).
```

Every combat roll appears in the log with its full breakdown (F1). Tooltips and log
text are **generated from the same registries and formula code the sim executes** — no
hand-written numbers, so tooltips can't lie (BB's Goedendag bug).

**Staged rollout (decided)** — the resolution is always "one d100 under the chance";
the modifier list grows with the milestones, never the mechanic:

- **M0/M1**: `skill − defense + weapon accuracy + height (±10/level) +
  surround (+5/extra attacker) + long thrust (−15 on any 2-hex melee attack) +
  special accuracy mods (瞄准 +10, 横扫 −10) − ranged per-hex falloff`, clamp 5–95;
  the simple morale multiplier (3 states, ×1.0/0.9/0.7 — scales attacker skill and
  defender defense); flails ignore the shield's base defense; 举盾 doubles it.
  That is the complete M0 list — nothing else. The player always sees one number;
  hover shows the parts.
- **M2**: injuries' stat multipliers, night (×0.7 ranged), defense soft cap (>50
  counts half).
- **M3**: terrain multipliers (paddy ×0.75), full 6-state morale, Lone-Wolf-style
  technique multipliers.

### 3.4 Vision

Each unit has a Vision stat (default 7 hexes): caps ranged targeting and what's spotted
in forests. **Heavy helmets reduce Vision** — the second counterweight (besides 坠气)
that keeps "always wear the heaviest helmet" from being degenerate. Night: −2 Vision on
top of the ranged penalty. Each elevation level: +1 Vision and +1 bow range. On the
overworld, terrain and night shrink sight radius. *(M0 deferral, recorded v0.21:
vision/fog is pushed to M1 — neither implementation has a Vision stat; the only piece
live in M0 is +1 bow range per elevation level.)*

### 3.5 Morale — the cascade engine

Six states (Unbreakable→Fleeing), flat multipliers per state *(the full 6-state ladder
incl. ×1.1 is M3; M0 ships three — Steady/Wavering/Fleeing at ×1.0/0.9/0.7)*. Checks
are never pre-announced; **after resolution the log shows trigger, base Nerve 胆识,
every modifier, the roll, and the resulting state** (F1) — implemented as of v0.24:
a check is `d100 ≤ 胆识 + 3 × adjacent allies + situational mod`, and both engines
carry the full breakdown (base / adj / mod) on every morale event, so the log prints
each term, not just the combined target. M0 triggers: taking ≥15 HP in one hit (−10);
an ally dying within 5 hexes (−15 if a leader, a further −10 from 斩首 terror).
Triggers scale with victim importance and
proximity. Routing the enemy is a victory condition. The banner-bearer (旗手) radiates
resolve — and the bureau's 镖旗 is a real in-fiction object (§5.5). Pure Lotus fanatics
never check; ghosts attack Nerve directly (the social stat doubles as anti-magic).

Known flow rule (both implementations agree, pinned): a kill's ripple morale checks
resolve **before** the end-of-battle check, and a 横扫 sweep keeps swinging at its
remaining adjacent victims after the battle ends — so morale/hit events can trail
`battle_end` in the log. The winner is locked by the over-guard; the trailing events
change nothing.

### 3.6 Positioning rules

- **Zone of control**: leaving an adjacent enemy's reach triggers a free strike from
  each adjacent foe; *a hit cancels the move*. Escape tools (Crane Step, ally swap,
  smoke bombs 烟雾弹) are real purchases. Cost rule (BB, implemented): AP and Breath
  for the **whole intended path are spent up front** — a ZoC- or spearwall-blocked
  move does not refund the unwalked remainder. A cancelled move still costs.
- **Surround**: +5 hit per melee attacker on the target beyond the first (fleeing
  allies don't count toward the ring). Implemented attacker-side — under M0's linear
  math identical to "−5 effective defense per extra attacker"; when the M2 defense
  soft cap lands, the two diverge and the term must move to the defense side.
  Explicit rule (BB's documented oversight, fixed): **never applies to friendly fire**.
- **High ground**: ±10%/level; the AI values hills (v0 AI: simple tile-preference rule).
- **Night**: ranged skill and ranged defense ×0.7, −2 Vision — attack the crossbow camp
  at night. Strategic scheduling as tactical counterplay.

### 3.7 Ranged combat: falloff, cover, scatter

**Minimum range 2**: bows and crossbows cannot fire at an adjacent enemy — a pinned
archer must break away through ZoC or switch to a sidearm (4 AP), which makes closing
on shooters a real tactic and sidearms a real purchase.

Per-hex falloff by weapon (bows gentle, thrown steep). **Line of fire**: shooting
through blockers multiplies chance ×0.25; a blocked miss can stray into the obstacle.
Shots over an ally at exactly 2 hexes are safe. **Scatter**: a missed shot at range >2
can hit a unit adjacent to the aim point (shields protect; ×0.75 damage) — firing into
a melee scrum is tempting and genuinely dangerous to friends. **Ranged friendly fire is
ON from M1** (it's the archer's core risk decision) — but, consistent with §3.6,
*surround bonuses never apply to it*. *(M1 deferrals, recorded v0.21/v0.24: scatter
AND the line-of-fire ×0.25 blocker rule — M0 has neither; M0 shots fly true and can
only target enemies, so the only friendly fire in M0 is 横扫 sweep, §3.10.)*

### 3.8 Retreat and withdrawal

Ordering a withdrawal is a per-man action: each escort must reach the deployment edge
alive — free strikes apply, fleeing men exert no ZoC, and **the struck-down save (§3.9)
is disabled while retreating** (so retreat-spam can't launder casualties). The fallen's
gear is lost with them. Campaign cost: −fame, contract failure penalties, possible
pursuit on the overworld. Retreat is a core skill — "know when to say no". *(M0 ships
only the involuntary rout-flee path; the ordered per-man Withdraw command joins the
schema in M1.)*

Implemented rout numerics (M0, both engines): a fleeing man's upkeep first attempts a
**rally — only with no adjacent enemy**, at `d100 ≤ 胆识 + 10 × rounds fled`, and
recovery is to **Wavering only**, never straight to Steady. Otherwise he runs toward
**his own deployment edge column** (player col 0, enemy the far column); on reaching
it he has *escaped* — removed from the field, counted toward elimination (溃走 in the
battle summary), gear and all.

### 3.9 Injuries — the tactical↔strategic bridge

*(All of §3.9 is M2 — neither implementation has wounds or the struck-down save yet;
in M0 a man at 0 HP is dead.)*

- **Temporary**: any hit ≥10 HP can wound (threshold = % of max HP); wounds degrade
  stats mid-fight and take days + medicine (金疮药) to heal.
- **Permanent**: at 0 HP, 33% chance to be *struck down* instead of killed — alive with
  a permanent scar (missing eye, broken knee, night terrors). Not while retreating; not
  from poison/bleed. Treatment at the 医馆 (physician); the temple 寺/观 handles the
  soul (mood, trauma, funerals).

### 3.10 Weapon families (the wuxia mapping)

Grip is the first axis, BB-faithful: **one-handed** weapons pair with a shield — or,
with an empty off-hand, are double-gripped for **+25% damage**; **two-handed** weapons
forbid shields and strike at 6 AP (one big swing per turn), buying **one premium axis**
at roughly twice the 1H number (BB's 2H scaling):

- **Reach line** (BB pike/billhook): 枪 long spear, 关刀/戟 — 2-hex attacks, the
  second-rank killer.
- **Damage line** (BB greatsword/greataxe): 斩马刀, 大斧, 大刀 — ~2× 1H damage,
  head-hit bonuses, AoE arcs (Round Swing −10 acc), terror.
- **Armor line** (BB 2H hammer/mace): 大锤, 狼牙棒 — armor effectiveness ×2, heavy
  Breath drain on hit (20, **replacing** the −5 baseline, §3.1), stun verbs; strips
  any tank in 2–3 swings, then crushes.

Beyond grip, families differentiate along the resource axes — AP, Breath, armor
knobs, reach, verbs:

| Weapon | BB analog | Identity / verbs |
| --- | --- | --- |
| **Jian 剑** (straight sword) | Sword | Accurate (+10), Riposte; the duelist's tool |
| **Dao 刀** (saber) | Cleaver | Bleeding wounds, Decapitate; the killer's tool |
| **Qiang 枪** (long spear) | Spear + Pike | **Two-handed, 2-hex reach** (long thrust −15 acc unless mastered), +20 thrust accuracy, **Spearwall** (free strikes on approach; anti-cavalry). 短矛 short spear is the 1H+shield variant |
| **Chui 锤** (mace/hammer) | Hammer | Armor destruction verbs (×1.5–2 armor damage) |
| **Fu 斧** (axe) | Axe | Split Shield *(deferred with shield durability)*, +50% head-hit damage Chop (×2.25) |
| **Guandao 关刀 / Ji 戟** | Polearm | 2-hex reach, −15 acc unless mastered. **戟 implemented** (2H reach 2, acc 12, 22–32, armor_eff 1.0, pierce 0.35, 6 AP/15 Breath, 坠气 5) — reach *and* the round swing: it carries 横扫. **大关刀 implemented** as the family's 1-hex heavy blade (2H, acc 8, 28–42, armor_eff 1.2, pierce 0.30, 6 AP/17 Breath, 坠气 6, chop ×2.25 head, bleed, 横扫). Generic 关刀 future |
| **流星锤 / 九节鞭** (meteor hammer / nine-section whip) | Flail | Ignores shield defense (a raised shield's extra still counts); head-hunter — 九节鞭 +10% head chance, **兜头 headhunt** (5 AP/16 Breath) is the gamble swing: forces the head hit at **×2.0** but at **−15 accuracy**, and a whiff **overswings for 15 extra Breath** (a full turn's recovery, and initiative sinks with it). Data-driven `head_mult`/`acc`/`miss_br` on the special. 流星锤 future |
| **Bi shou 匕首** (dagger) | Dagger | Puncture: 100% armor-pierce, 0% armor damage |
| **Gong 弓** (bow) | Bow | Range 7, falloff per hex; volume of fire |
| **Nu 弩** (crossbow) | Crossbow | Flat power, armor-piercing; 连弩 repeating variant: 3 weak bolts |
| **暗器** (hidden weapons: 飞刀, darts) | Throwing | +20 acc close, useless far; by jianghu tradition, the same 镖 as the bureau's name |
| **斩马刀 / 大斧 / 大刀** (2H damage line) | Greatsword/Greataxe | ~2× 1H damage, +5 head chance, AoE arcs, terror |
| **大锤 / 狼牙棒** (2H armor line) | 2H Hammer/Mace | Armor effectiveness ×2, 20 Breath drain on hit (replaces the −5 baseline), stun verbs. **碎甲 demolish** (6 AP/20 Breath, reworked v0.24): armor damage = dmg ×3 capped at the armor present; then blunt trauma through what's left — HP = dmg × pierce − 10% of the armor *remaining after the strip*; no head multiplier, no overflow channel — the ×3 is the verb. 狼牙棒 future |

Every family also declares its 坠气 by heft — dagger 1 … crossbow/long spear 4,
great-axe/戟 5, maul/大关刀 6 (§3.1) — the third cost axis after AP and per-strike
Breath.

Two cross-family verbs, pinned as implemented (M0):

- **横扫 sweep** — carried by **three** weapons: 大斧, 戟, 大关刀. 6 AP / 20 Breath,
  −10 acc, one swing at **every unit in the adjacent ring, friend and foe** (reach
  weapons still sweep only the adjacent ring) — M0's only source of friendly fire
  (§3.7), and 围攻 never applies to it (§3.6).
- **Bleed** — 腰刀/砍刀/九环刀/大关刀: any hit dealing **≥6 HP** sets 2 bleed ticks —
  5 HP at each of the victim's next two upkeeps; re-application refreshes the count to
  2 (no stacking); set even on a killing blow (inert on the dead — JS parity).

M0's shipped arsenal (sim `data.py` = `game.js`, 14 weapons): 长枪 · 短矛 · 腰刀 ·
砍刀 · 九环刀 · 短刀 · 大锤 · 大斧 · 戟 · 大关刀 · 九节鞭 · 匕首 · 猎弓 · 弩 — the
rest of the table (剑, 流星锤, 暗器, 连弩, 斩马刀, 大刀, 狼牙棒, generic 关刀) is the
v1 target arsenal, post-M0.

Shields (rattan 藤牌, lacquered round, pavise) keep the BB triangle: axes split them,
meteor hammers ignore them, everyone else respects them. **Raise Shield (举盾,
BB's Shieldwall)**: 4 AP + 10 Breath, doubles the shield's defense bonus until the
bearer's next turn; later, +5 more per adjacent ally also raising (the wall). **Weapon
durability** drains slowly vs armor, never vs flesh *(durability — weapon and shield —
is deferred past M0; the axe's Split Shield verb waits on it)*.

### 3.11 Equipment quality grades (品阶)

Five grades, orthogonal to item identity — BB's named/famed-item ladder made
systematic. Both implementations carry exactly this table:

| Grade | Color | Damage | Accuracy | Protection | 坠气 |
| --- | --- | --- | --- | --- | --- |
| 凡品 fan | white `#9b9b9b` | ×1.00 | +0 | ×1.00 | ×1.00 |
| 良品 liang | green `#3f8f4a` | ×1.10 | +2 | ×1.15 | ×1.00 |
| 精品 jing | blue `#3873b8` | ×1.20 | +4 | ×1.30 | ×0.95 |
| 珍品 zhen | purple `#8a4bb0` | ×1.35 | +7 | ×1.50 | ×0.90 |
| 神品 shen | orange `#d2691e` | ×1.50 | +10 | ×1.75 | ×0.85 |

**Quality buys numbers; family buys verbs.** AP, per-strike Breath cost, reach, hands,
armor-pierce, armor-effectiveness, and special attacks are quality-immune — a 神品
dagger is still a dagger (100% pierce, zero armor damage), just sharper and surer, so
pillar 4 survives the loot ladder. Weapons scale both damage ends (rounded) and add
flat accuracy; the 坠气 multiplier lightens **all** equipment at high grades — graded
gear is finer-made, so armor scales protection **up** and 坠气 **down**, and a 神品
maul hangs lighter on the back than the smithy's plain one (light weapons mostly round
back to base — rounding favors the heavy end). The high-grade piece guards like iron
and taxes Breath like leather, exactly the trade BB's famed armor sells. Labels prefix the grade above 凡品: 精品·腰刀.

Wiring: one `QUALITY` registry per implementation; roster templates and scenario JSON
units take optional `wpn_q` / `wpn2_q` / `armor_q` / `helmet_q` (default 凡品), scenario
overriding template — the battle-test knob. Quality applies at unit creation to the
deep-copied item; base tables never mutate, and breath_max reads the quality-adjusted
坠气. This retires the ad-hoc `*_fine`/`*_crude` weapon variants (刘三刀's fine
saber is now plain 腰刀 at 精品; the crude bow becomes the 凡品 猎弓 baseline). 神品 is
the top rung of §5.3's loot-repair-resell ladder and where "every blade has a name"
turns literal — named blades are 神品.

---

## 4. Characters

### 4.1 Eight attributes

HP 体魄 · Breath 气力 · Nerve 胆识 · Initiative 身法 · Melee skill 武艺 · Ranged skill 准头 ·
Melee defense 招架 · Ranged defense 闪避

### 4.2 Backgrounds (the attachment engine, part 1)

~25 at v1 (6 in the vertical slice — §7.1). Each defines stat ranges, price, wage, gear,
excluded traits, XP modifier, unique events, and a retirement epilogue.
**Recruits are men and women** — 女侠 are genre-core (Water Margin's Hu Sanniang and Sun
Erniang); gender-aware string keys go into the data architecture from day one (the BB
postmortem's "can't be undone anymore" lesson).

farmhand 佃农 · porter 脚夫 · reformed bandit 退伙强人 · deserter 逃兵 · **defrocked monk
还俗僧** (high Nerve, brawler's strength — the 鲁智深 archetype) · **down-and-out Taoist 落魄道士**
(lore events, exorcist-fraud flavor) · salt smuggler 私盐贩 · boatwoman/boatman 船夫 ·
hunter 猎户 · butcher 屠夫 · blacksmith 铁匠 · **performer 伶人** (acrobatic 百戏
training is real — high initiative; in this era performers famously gained court rank,
per 《伶官传序》 — rich event hooks; NPCs may sneer 戏子 in dialogue, where the period
contempt belongs) · beggar 乞丐 (Beggars' Sect events) · physician's apprentice
医馆学徒 · failed scholar 落第书生 (the exams limp on) · ex-yamen runner 衙役 ·
wandering swordsman 游侠 (expensive, deadly) · **sword master 剑客** (brilliant, old,
fragile) · executioner 刽子手 · miner 矿工 · fisherman 渔夫 · **coroner 仵作** (forensic
examiner — hooks into hauntings and the Restless Dead; recognizes 赶尸 marks) ·
tea picker 茶农 · caravan guard 趟子手 (the Sellsword) · street acrobat 杂耍艺人 ·
**Khitan deserter 契丹逃卒** (fled the banners; superb rider's bow and Nerve, distrusted
in the south — the 萧峰 nod, and the player's window into the invader's humanity) ·
**ex-guard 牙兵** (a governor's personal guard, disbanded after a mutiny — skilled,
expensive, drawn from a trait pool heavy on Insubordinate/Greedy; the era's most
dangerous résumé)

### 4.3 Hidden depth (part 2) — and what money can never buy

- **Talent stars**: 3 of 8 attributes get 1–3 stars (60/30/10%), widening level-up
  rolls; 1 star ≈ +5 by max level.
- **Traits**: 0–2 hidden (Iron Lungs, Greedy, Brave, Drunkard, Huge, Clumsy…).
- **Graduated reveal, capped (F6)**: gossip = traits; physician exam = talent *count* +
  one chosen attribute's range. **Never the full star map** — stars are revealed by
  level-up rolls, preserving the discovery arc (the farmhand who turns out to be a
  three-star prodigy) and keeping background pricing meaningful.

### 4.4 Progression

- Levels 1–11 (XP 200…15000, combat-fed only — see F9), 1 technique point + raise 3
  attributes per level. Veteran levels: +1s, no points.
- **Techniques (武学)**: 7 tiers, spend-gated. Tier 4 = weapon masteries (精通). Tier 6
  fork: **轻功 Lightness** (light, initiative→defense) vs **铁布衫 Iron Shirt** (heavy
  armor mastery).
- **Secret manuals (秘籍)**: rare loot from elite contracts, crises, and legendary
  sites — **true chase upgrades** (the endgame fuel, F4), hard cap **one manual per
  escort**, tradeable. *Content rule: all manual/technique names original or
  public-domain (Water Margin, 游侠列传, generic vocabulary like 铁头功/铁布衫) — never
  Jin Yong's named creations (his estate litigates).*
- **Sworn brotherhood (结拜)** — deliberately tiny system, capped 2–3 pairs per roster:
  events can offer two escorts an oath (shared background, one saved the other).
  Adjacent: small Nerve aura. If a sworn sibling dies in sight: immediate morale check,
  then a permanent grief-or-vengeance trait fork. Epilogues reference surviving
  siblings. Water Margin's actual engine, BB's most-requested relationship system —
  and native to the era: the Five Dynasties organized loyalty by oath and adoption
  (义儿 corps, 十三太保). Permadeath converted into story, mechanically.

### 4.5 Modular anatomy (the BB paper-doll, made explicit)

Every character is assembled from modules — **one structure serving mechanics, visuals,
and data at once** (confirmed BB-style):

- **Mechanical slots**: head (helmet = the head-armor pool, §3.2) · body (armor = the
  body-armor pool) · main hand (weapon = the verb set, §3.10) · off hand (shield /
  empty for double-grip +25% damage) · ammo (quiver — *M0 deferral: neither
  implementation tracks ammo; bows and crossbows shoot unlimited until the quiver
  slot lands*) · accessory (sash, banner,
  trinket). Every slot's item is a JSON entity carrying stats, 坠气 (the carry tax,
  §3.1), durability, and a sprite-layer reference (§7).
- **Visual layers**: the bust composites in fixed order — base face/hair (generated
  from background, gender, age) → body-armor layer → helmet layer → held weapon +
  shield layers — each keyed to the **same item ID** as the mechanical slot. What you
  see is literally what is equipped, at any zoom: BB's core readability win, and the
  reason §6 budgets art per gear item rather than per character.
- **Faces remember**: permanent injuries add scar/eye-patch overlays (small overlay
  set; deferred past M2). Heavy helmets visibly cover the face — the Vision tradeoff
  (§3.4) you can read at a glance.

### 4.6 Roster and bench

Roster cap 20; **12 fielded** by default. Benched escorts draw full wage (pressure),
heal and train in camp, swap in/out only in settlements. **Contract difficulty reads
the strongest 12** (as BB) — bench depth is insurance and rotation, not hidden power.

---

## 5. Campaign layer

### 5.1 The world

Procedurally generated per campaign: **~17 settlements** (2 prefecture cities 府城, 3
county seats 县城, 6 market towns 市镇 + villages, garrisons 军镇/戍堡) split among 3
military provinces (藩镇), plus the **Northern Marches** border strip (§2.1) — fewer,
poorer, more dangerous settlements with frontier contracts and horse smuggling. Each
settlement has 1–8 **attached works** — tea plantation, silk farm, salt
well, jade mine, kiln, herb garden, lumber camp, fishery — setting what's cheap there,
which recruits appear, which contracts spawn. Caravans actually travel; bandits actually
raid them; prosperity actually drops when they do — contracts land because the fiction
is verifiable in the simulation.

Real-time-with-pause overworld; day/night cycle; vendors close at night; wages daily.

### 5.2 Settlements: buildings & situations

Marketplace · weaponsmith 铁匠铺 · armorer · fletcher · **physician 医馆** (injuries,
recruit exams) · **temple 寺/观** (mood/trauma, funerals) · **teahouse 茶馆** (rumors,
recruit gossip) · tavern 酒馆 · **martial hall 武馆** (paid training) · **leitai 擂台**
(1v1 challenge fights by default — the iconic duel; every 5th match a special team
bout, unique prize gear) · harbor 码头 (river travel) · pawnshop 当铺 · black market
(low-Xia access)

**Settlement situations** (~15 at launch): temporary tags — Raided 遭劫 · Besieged 被围 ·
Well Supplied 丰足 · Drought 大旱 · Plague 瘟疫 · Festival 庙会 · Bandit Roads 路霸 … —
each with **numeric, tooltip-visible effects** (F1) on prices, recruit/item availability,
and which contracts spawn. Sim-caused, contract-clearable; when permanent destruction is
off, crises apply situations instead of deleting settlements. This is the world's
"simulation runs without you" feedback channel.

### 5.3 Economy

- **Contract pay** = base × skull_multiplier^1.3 × fame clamp (1.35–2.7) ± haggling.
  **Roster strength never enters the pay formula** (it drives spawn difficulty only —
  the BB split that keeps paid work fair while the wild stays dangerous).
- **Spawn difficulty** scales on a composite of roster level *and equipment value* (so
  sparring-trained but poor companies aren't overmatched). Marginal-recruit rule,
  stated: new hires below company-average level contribute fractional strength for
  their first 10 days.
- **Haggling**: the client's patience is **diegetic** — a readable facial state
  (calm / terse / irritated), fuzzy but honest (pillar 3). Push-your-luck preserved,
  hidden-meter mistrust avoided. Every haggle option is at least situationally correct.
- **Currency**: copper cash 文, counted in strings 贯 (the era's daily money); large
  contracts pay partly in silk bolts 绢 or silver ingots — era-accurate.
- **Wages** ×1.1 per level; fame decays daily; food spoils; tools burn; medicine
  drains; ammo refills cost. Four consumables, each mapping to one failure mode.
- **Trade goods**: tea 茶 · silk 丝绸 · salt 盐 (state monopoly — smuggling contracts) ·
  porcelain 瓷器 · jade 玉 · lacquer 漆器 · herbs 药材. Full-value cargo; the pacifist
  income line (paying in fame and silver, not XP — F9).
- **Loot-repair-resell** is the real combat income — taught by onboarding (F14).

### 5.4 Standing — three tracks, all of them working

- **Fame 名声**: contract-pay multiplier + unlocks + **the parley system (§5.5)**;
  decays daily.
- **Relations** (per settlement): prices; drifts to neutral.
- **Xia 侠义** (0–100, start 50): extremes are content, middle is merely perk-less
  (F11); drifts toward 50.

### 5.5 The trail call (喊镖号) — fame-gated passage

The most biaoju-native mechanic in the source material, and one BB structurally cannot
have. On bandit interception during escort work, the 趟子手 walks ahead shouting the
trail call; outlaws who respect the bureau's name let the convoy pass. Mechanically: a
pre-battle **parley check** on Fame — modified by Xia, cargo value, and whether you've
previously slaughtered or spared this region's outlaws — with three outcomes: **pass
freely / pay a face-saving toll (买路钱) / fight**. The bureau's 镖旗 banner is the
in-fiction object of recognition (and the banner-bearer's mechanical role gets its
fiction). Fame decay now genuinely hurts: a faded flag stops opening roads. The rival
bureau's dirtiest trick: flying a forged flag — an authentic jianghu plot.

### 5.6 Contracts (F5: templates × twists)

~10 templates at v1 (2 in the slice): escort cargo 押镖 (the namesake) · clear
stronghold · patrol roads · beast hunt · deliver sealed item · guard dignitary · siege
relief (crisis) · jailbreak (low-Xia) · investigate haunting · **frontier templates**
(Marches + invasion foreshadowing): ransom captives back from a 打草谷 column ·
evacuate a border village · scout the passes.

**劫镖 battlefields**: escort-contract ambushes generate the road through the tactical
map (with its half-Breath lane, §3.1) and place the **convoy cart 镖车** on it — an
impassable centerpiece the deployment forms around. The cargo is *visibly* the thing
being fought over; later, cart-adjacent objectives (defend N turns, bandits try to
drag it off) can grow from the same seed.

**Military contracts (军务)** — the BB noble-contract analog, and the "fight as
soldiers" path: offered by the provincial courts (藩镇), unlocked at Professional fame
via ambitions. Patrol for a province · stand in a jiedushi's battle line (pitched
battle alongside provincial troops) · assault or hold a stronghold · raid a rival
province's supply train. **Any company can take them** — the soldier's life is a
career choice, not a separate mode; the Broken Garrison origin simply starts there.

Twist tables per §1.2 F5: flavor twists common, difficulty twists rare/bounded/cooldown,
neither in the F3 window.

### 5.7 The rival bureau (signature system — redesigned after review)

One procedurally generated rival escort bureau per campaign — named master, famed
blades. **Growth is a parallel clock**: it advances with elapsed days and *its own
simulated contract record* (it can lose men to the same world), **never inversely with
player stagnation** (pillar 1's corollary — no kick-while-down). Interference is capped
(at most one rival event per ~10 days; no tolls/theft while player fame is below a
floor), and your home region gives you a defensible bidding base.

It bids on contracts, duels your champion at the leitai, occasionally flies a forged
flag (§5.5). **The endgame confrontation is asymmetric, not a mirror**: their prepared
ground (fort, pre-claimed high ground, pavise crossbow line), their full roster against
your fielded 12, named elites carrying unique manuals — a multi-battle gauntlet that
taxes roster depth and the injury system. Legible math, no stat-cheats, and a finale
that tests everything the campaign taught.

*Honest cost: 2–3 months. Degradable v1-minimum: named rival as a contract-market
modifier with flavor text + one leitai duel + the endgame challenge.*

### 5.8 Events & mood

Background-keyed text events on road and in camp (the reformed bandit recognizes this
stronghold; the monk and the butcher argue over a chicken; the opera fighter stages a
play that restores company mood). **Mood** (per escort, 7 states) converts strategic
failures (no pay, no food, dead friends) into starting combat morale — one legible
bridge stat.

### 5.9 Origins, ambitions, endings

- **Origins** (3 at v1; the slice ships only the default). Origins are the answer to
  "what is this company?" — the same campaign systems re-weighted:
  - **Ruined Bureau 破落镖局** (default): the escort fantasy — 押镖 contracts, the
    trail call, the rival bureau arc.
  - **Broken Garrison 残旗溃卒**: ex-provincial soldiers under their old banner — the
    soldier fantasy. Military contracts and one province's favor from day one; starts
    with drilled spear-and-crossbow men and army gear; penalty to civilian fame and
    escort work (merchants distrust soldiery); the rival is a rival *commander*, not a
    bureau.
  - **Lone Swordsman 独行客**: single wage-free veteran — *an ordinary, unusually good
    fighter: their death does NOT end the run while the company can hire.*
  - Post-v1: Shaolin Lay Brothers · Golden Basin (金盆洗手 — ex-bandits gone straight,
    half the map hostile) · Salt Smugglers · Performer Troupe 伶人班.
- **Ambitions**: player-chosen milestones, +fame, evaluated continuously (F10).
- **Retirement endings**: 5 graded endings; score divides by days elapsed and
  multiplies per crisis survived. Every escort's epilogue flavored by background —
  and by surviving sworn siblings.

### 5.10 Difficulty & saves

- Orthogonal knobs: combat / economy / starting funds; enemy stats never change.
  Beginner = ±5 hit-roll shift in player's favor only.
- Ironman opt-in. Suspend save per F2. Days 1–15 ramp per F3.

---

## 6. Art & audio direction

Steal Battle Brothers' constraint-turned-identity:

- **Bust-style figures** on faction-colored sockets — every piece of visible gear
  rendered. Style: **bust-crop framing applied to the Ming woodblock idiom** — 陈洪绶's
  水浒叶子 and Ming illustrated-novel prints (绣像) as the style source (those are
  full-figure; the bust crop is our BB inheritance — honest citation). Ink lines, flat
  mineral pigments, paper texture.
- **Pipeline reality (from review)**: the cost is not the base bust, it's gear-layer
  combinatorics. M1 includes an explicit pipeline-validation deliverable: one fixed
  pose/camera, style-LoRA on public-domain 绣像 scans, 4 busts + 4 weapon overlays
  end-to-end, timed. Budget 0.5–1 day per gear-visible item; if cleanup exceeds
  ~1 hr/asset, fall back to silhouette-flat gear layers (solid ink shapes — hides AI
  artifacts, cuts cleanup 5×). M1–M2 needs only ~25–40 finished sprites. Steam AI
  disclosure applies; the audience skews hostile to visible AI art — cleanup matters.
- Tonal contrast rule: elegant print aesthetic + brutal outcomes. A decapitation in
  woodblock style.
- Audio: guqin/pipa/dizi sparse ambient; war drums 战鼓 in battle; one erhu theme for
  funerals. Foley over music in fights.
- **No facing/flanking** — busts can't show direction (BB's exact cut, inherited
  consciously).
- **Typography** (decided for the prototype; recommended for production — all
  open-licensed and safely embeddable in a commercial game):
  - Primary UI, body, dialogue: **霞鹜文楷 LXGW WenKai** (SIL OFL) — ink-brush regular
    script, warm and readable. (朱雀仿宋 was trialed as primary in the prototype and
    **rolled back by user verdict 2026-06-11** — too mannered for body text.)
  - Display/titles: **京华老宋体 KingHwa OldSong** (free for commercial use) —
    old-style Song with woodblock-print flavor, matching the 绣像 art direction.
  - Dense UI (combat log, stat tables, numbers): **思源黑体 Noto Sans SC** (OFL).
  - Document/contract flavor screens only: **朱雀仿宋 Zhuque Fangsong** (OFL) —
    imperial-document register (re-download from github.com/TrionesType/zhuque when
    that screen exists; removed from the repo in the v0.12 cleanup).
  - **Licensing rule: never ship system CJK fonts** (SimSun, KaiTi, any 方正/汉仪/华文
    family) — they are not licensed for commercial embedding and CJK foundries
    litigate aggressively. OFL fonts may be embedded and subset freely.
  - Practical: full CJK fonts are 5–15 MB — subset to woff2 for web builds
    (pyftsubset); Godot 4 consumes the TTF/OTFs directly with font fallback chains.

---

## 7. Technical architecture

Full comparison in `RESEARCH.md` (tech-stack section). Decisions:

- **Engine: Godot 4.x, typed GDScript** (Python-like). Free/MIT, 2D-first, best
  built-in UI toolkit — and this game is 70% UI. C# escape hatch if profiling demands.
- **Engine-agnostic simulation core**: all rules/state/AI as plain objects, no
  rendering deps. Godot scenes replay sim events. Headless tests, deterministic
  replays, simple saves, free instant-resolve (F8).
- **Pathfinding lives inside the sim core** (a ~50-line Dijkstra over the sim's own
  hex graph, not engine AStar2D) — otherwise deterministic replay breaks.
- **Everything is data**: items/techniques/enemies/contracts/events as JSON, stable
  string IDs (`weapon.qiang_militia`, `tech.iron_shirt`), registries, hot reload.
  **All strings in external tables with stable keys from M1** (bilingual becomes a
  translation task, not a rewrite; gender-aware keys from day one).
- **Single source of truth for tooltips**: UI text generated from the same registries
  and formulas the sim executes (F1's credibility depends on it).
- **Seeded named RNG streams** (combat / AI / loot / worldgen); command-
  pattern turn resolution; integer math. Replay = seed + command log (this is what
  makes F2's suspend save nearly free once mature).
- **Utility AI** — scoped honestly (review: "the AI fights for hills" costs months).
  v0 (M0–M1, as implemented in `sim/ai.py` = `game.js aiTurn`): greedy over **hit
  chance** (not expected damage), ties to the lower-HP target. Family special rules,
  checked in order before the basic strike: 斩首 on the first target under 40% HP ·
  横扫 with ≥2 adjacent foes and **0** adjacent friends · 瞄准 when the best shot is
  under 55% · 碎甲 on the first target with body armor ≥50 · 兜头 on the first with
  head armor ≤15, and only from ≥50% base hit chance — the gamble's whiff costs 15
  extra Breath, so the AI doesn't bet from a weak hand. Hand rules: a pinned archer
  (enemy adjacent) swaps to the sidearm;
  archers kite to ≥3 hexes and advance when out of bow range (range + elevation);
  spear-bearers set the wall when the nearest enemy closes to 2–3 hexes; out-of-attacks
  shield-bearers raise against adjacent foes; `"garrison": N` units hold within N hexes
  of their post; move scoring prefers high ground. 8-action safety cap per turn; fully
  deterministic — the reserved "ai" RNG stream is not consumed yet, so AI changes never
  perturb combat rolls. (The v0.2 "don't break engagement under ZoC" rule was never
  implemented — future, with influence maps, JSON personalities, temperature: M3+.)
  AI is a permanent ~20% tax on every milestone, not a line item.
- **Overworld: a FIXED, hand-authored historical map** (v0.29 decision — our
  deliberate divergence from BB's procgen: the map IS the setting). The
  historical macro-regions 河北 · 河东 · 河南 · 关中 · 山东 as authored region
  files with real cities and **anchored set-piece sites** (虎牢关 is always the
  duel; 滹沱桥 always the bridge fight). Procgen is demoted to minor per-campaign
  scatter (lair/camp placement); world state serializes as plain data.
- **Saves**: to_dict/from_dict per system, version int from day one, flat tables keyed
  by stable IDs, gzip. Never load engine Resource files from user folders; JSON only.
- **Moddability tiers**: (1) JSON content packs with load order + ID override — free
  with the data-driven design, ships v1; (2) script mods (Godot Mod Loader) and
  (3) asset overrides — post-v1.

### 7.1 Milestones (side-project calendar, honest ranges)

**M0 — Python combat prototype (1–2 months).** Pure-Python deterministic sim with
pytest: axial hex math (orientation + parity locked), initiative, AP/Breath, two-layer
damage, hit formula, 3-state morale, ZoC, **retreat**, vision, 4 weapons covering the
resource axes (枪 spear: accuracy+spearwall · 刀 saber: bleed · 锤 mace: armor-crack ·
弓 bow: ranged+scatter), shields, AI v0. 6v6, two maps (flat / one hill), text render.
**Exit criterion — "rules sound, schema locked," NOT "fun"** (fun lives in M1):
pytest green; AI-vs-AI batches show no dominant strategy across the 4 weapons;
damage/hit distributions match BB reference values. Batch simulation is this
developer's unfair advantage — keep the tooling forever, but hard-stop the milestone.
*(Scope deferrals, recorded v0.21/v0.24: vision/fog, ranged scatter, the line-of-fire
×0.25 blocker rule, and the ordered Withdraw command were consciously pushed to M1 —
neither implementation has them.)*

**M1 — Godot vertical slice (3–5 months).** Port core to typed GDScript. One battle:
8v8, the 4 families, shields, one hill, routs working. UI: **hit-chance tooltip with
full breakdown + comparison tooltip** (the F1/F13 down-payments), plain-text log, one
default formation. **Juice is a closed list**: hit-flash, HP/armor bars, floating
damage numbers, ~12 free SFX, corpse sprite-swap, camera shake on crits. Nothing else.
Art-pipeline validation deliverable (§6). **Kill/pivot checkpoint: if the skirmish
isn't fun to replay 10 times with placeholder art, revisit the design before building
the campaign.**

**M2 — Minimal campaign loop (3–5 months).** Hand-authored map (NO procgen), 2–3
settlements, 4 buildings (market, smith, physician, tavern). 6 backgrounds (farmhand,
reformed bandit, hunter, defrocked monk, caravan guard, wandering swordsman — covers
the price curve), 8 traits, 2-tier recruit info (look + exam). 2 contract templates
(押镖 escort + clear stronghold), one shared 4-twist table. Bandits as the only faction
(3 tiers). Economy: wages + food + repairs (no haggling meter, no trade goods, no fame
decay, no Xia). Levels 1–5; 9 techniques in 3 tiers. Injuries persisting, permadeath,
mood at 3 states. Overworld saves only. 10–12 written events. **Exit: "one more
contract" compulsion works; economy KPI within tuning range (pillar 5).**

**M3 — The wide world.** The remaining hand-authored regions (河东 · 关中 ·
山东 + the Northern Marches; fixed historical map per v0.29), caravan/
prosperity sim, settlement situations, full event system, camp roles, leitai,
trail-call parley, fame decay + Xia, suspend save (replay infra is now mature).
Cheap second/third factions: deserters (human AI, better armor) and jiangshi (mechanics
you get by *skipping* systems — no fatigue, no morale). **M4 — The Khitan Invasion +
rival bureau + endgame ladder + origins.** Invasion faction ships as a scoped
composition: Han auxiliary spear-and-crossbow infantry (reuses human AI) + one cavalry
archetype (horse+rider unit with the Charge verb; horse killed → rider on foot) +
打草谷 column leaders. Full mounted-archer kiting AI is a post-v1 refinement. Then
polish → demo.

`game01_demo` scope = **M0 through M2**: realistically **9–15 months** of side-project
time. (Reference: BB took 3 experienced full-time devs ~4.5 years to 1.0. Unstated
timelines are how side projects die — hitting month 6 still in M1 is *on pace*.)

---

## 8. Out of scope (stated loudly)

**Forever (identity cuts):**

- Player avatar/hero on the field (the 总镖头 stays in fiction; Lone Swordsman is just a
  good wage-free man, not an avatar)
- Facing/flanking (art constraint, inherited consciously)
- Xianxia powers — grounded forever
- Authored story campaign (procedural sandbox + crises; we accept the perennial
  "where's the story" criticism, as Overhype did)
- Multiplayer; mobile
- Domestic PRC release SKU (gore + 僵尸/鬼 + sect themes make banhao unrealistic;
  "Chinese market" = Steam-global Simplified-Chinese players, who are underserved for
  exactly this genre)

**Post-v1 (deferred, not dead):**

- The two variable crises (War of the Provinces, Pure Lotus Rising — v1 ships the
  essential Khitan Invasion) · Pure Lotus faction · full Khitan mounted-archer kiting
  AI (v1 ships the scoped invasion composition, §7.1 M4) · beasts/yaoguai
  charm-illusion AI · endgame bounty board · origins beyond 2 · camp system beyond
  basic roles · leitai team specials · settlement permanent destruction · river
  travel · 18-man battles · repeating crossbow · mod tiers 2–3 · player-rideable
  mounts (enemy horse+rider units are a unit archetype, not a riding system) ·
  origins beyond the v1 three (Ruined Bureau, Broken Garrison, Lone Swordsman)
- **Retinue followers**: consciously folded into camp roles (F12)
- **Authored companions** (the second half of Overhype's Menace lesson): consciously
  cut for v1 — procedural identity + sworn brotherhood + the rival bureau carry
  characterization. Possible post-v1 hybrid: 2–3 handcrafted recruitable jianghu
  legends with small event chains

---

## 9. Open design questions (for our next discussion)

1. **Breath flavor** *(narrowed)*: pool flipped to depleting 气力 (v0.2). Remaining
   question: does exactly ONE tier-7 technique get an active Breath conversion (提气 —
   a once-per-battle second wind, grounded as breathing technique), or zero actives?
2. **Party size**: 12 fielded (current) — revisit 14–18 only post-v1?
3. **Field duels (单挑)**: leitai is 1v1 by default now (same UI/code as champion
   duels). Should *field* battles sometimes open with a champion-duel option with
   morale stakes? Cheap on the event layer; strong genre flavor.
4. **RNG streak mitigation** *(decision to record)*: is transparency + the 5–95 clamp
   the whole answer, or do we ship an optional "softened rolls" toggle (like
   Beginner's ±5) for the rage-quit demographic? Either is defensible; pick one.
5. **Language**: decided architecturally (external string tables, English-first
   authoring with Chinese terms, translate at demo-success signal). Remaining: do we
   write the *Chinese-facing* names (techniques, factions) bilingually from the start?
   (Cheap, and CN players will screenshot them.)
6. **Title**: **resolved — Shattered Jade (碎玉)**, final 2026-06-11.
7. **M1 demo bar** *(updated)*: 8v8, 4 weapon families, shields, one hill, routs,
   hit-chance + comparison tooltips. Night variant returns in M2 as a twist.
8. **Sworn brotherhood scope**: events-only (current, capped 2–3 pairs) — or should
   oaths also be player-initiated at camp (more agency, more degenerate-pairing risk)?
9. **How playable is the Khitan side?** Current design: Khitan-paid contracts exist
   during the invasion (deep Xia cost) but the bureau is structurally southern. Should
   a full collaborator path (working the invasion *for* the child-emperor's side, à la
   BB's noble-war side-picking) be in scope post-v1 — or does the game take a stance?
10. **Naming the realm**: the southern dynasty stays unnamed/procedural while the
   Khitan/Liao keep their real names (the 杨家将/天龙八部 convention). Comfortable with
   that asymmetry, or fictionalize the Khitan too?

---

## 10. Changelog

**v0.30 (2026-06-12)** — **the realm goes M&B: grand geography, modular areas,
and the playable web 舆图**. (1) **中原 grand map** (`world/zhongyuan.json`,
56×36 ≈ 2,000 hexes, generated with gap-proof hex-line drawing): the M&B fixed
strategic geography — NEW impassable **mountains** terrain makes ranges walls
(太行/吕梁/秦岭/中条/嵩山/燕山) pierced only by road-carved passes; the 黄河
great bend with 蒲津/孟津/白马 crossings; 27 settlements across 关中·河东·河南·
河北·山东·幽云, 10 anchored sites (潼关·虎牢关·井陉·天井关·拒马二渡…), 10
roaming parties. 镇州→太原 must thread the 井陉; 镇州→长安 is a 6-day ride.
(2) **Modular areas** (user direction): `world/realm.json` is the region
registry — **河北南部 is the pilot**; 河东·关中·西北·山东·淮南·荆楚·剑南·幽云
are registered as planned sockets that plug in via border exits (author one
JSON in the hebei/henan pattern, register, link). A test pins registry
consistency (symmetric links, built areas loadable). (3) **The web 舆图**
(`prototype_web/world.html`/`world.js`): the strategic map is PLAYABLE in the
browser — same paper-and-ink language as the battle page; click-to-travel with
path preview and day estimates, camp, provisions/day HUD, living parties,
hidden lairs, interception modal whose 「开战」 button opens the battle page
with the encounter's scenario (the first campaign→battle loop!); world picker
defaults to the pilot region. (4) **Stable edition is now two files**:
`release.py` also assembles `shattered_jade_world_vX.Y.html` (worlds embedded,
offline, battle links pointing at the battle release file beside it).
116 tests green.

**v0.29 (2026-06-12)** — **the fixed map: anchored sites + several regions** (the
deliberate divergence from BB: their procgen map is disposable; ours IS the
setting — §7 overworld bullet and §7.1 M3 rewritten, Voronoi procgen retired).
(1) **Anchored set-piece sites** override the terrain encounter table: 滹沱桥
(守桥) · 拒马东渡/西渡 (血战) · 黑风岭 (对决) in 河北; a lair's own scenario
also binds (黑风寨/嵩山贼穴 → 攻寨). Caught at a named place, you fight THAT
battle. (2) **Second region: 河南·京畿** (20×12, c. 942) — 汴州 the capital,
洛阳, 郑州, 滑州, the 黄河 with 白马渡/孟津渡, **虎牢关** as the duel pass, a
hidden 嵩山贼穴, its own caravan/patrol/band. (3) **Region crossing**: border
exit hexes link regions (赵州 road ↔ 滑州 over 白马渡); cross() carries the day
clock, provisions, and the event log; scenario references are validated against
scenarios/ at load — fixed map, fail loud. (4) **Verification pass on v0.2**
(3-agent adversarial review + 250-run fuzz; determinism/soak/stream-isolation
all PASS): fixed — razed bands now disband (no ghost ambushes), hidden lairs no
longer leak through their tile (kept natural terrain: no render hole, no cheap-
path tell, no travel-by-id to an undiscovered rumor), per-step spotting and
no slipping past a hostile at departure, starving emitted on battle days, day-
stamp consistency (dusk events stamp the day they happen), resupply only in
friendly un-razed settlements (camping in town restocks; 辽营 feeds no one),
bandit prowl is a real cost-paid march (no river hops), routed parties march on
day one, razed lairs render as 墟 ruins, two non-adjacent 官道 gaps repaired,
load-time validation of party homes/waypoints/kinds. 114 tests green.

**v0.28 (2026-06-12)** — **overworld v0.2: the BB living-world layer** (per the
RESEARCH.md campaign digest — the map is no longer scenery). (1) **Roaming
parties** tick daily: the 黑风团伙 prowls its 西山 leash drawn to the roads (raid
posture), the 绸缎商队 walks a trade loop 镇州–河间–沧州–定州, the 成德军巡骑
polices the 官道, and a Khitan 打草谷 column rides its circuit through the
frontier fords. The world grinds on without the player — bandits catching a
caravan emit `caravan_attacked` (the prosperity ripple lands with the economy,
M2). (2) **Interception is contact, not coincidence**: a hostile within 1 hex
stops the column mid-march; the encounter event names the battle scenario
**seeded by the world hex** (road→劫镖 · bridge→守桥 · ford→血战 · hills→攻寨,
data-driven in `world/*.json`) — caught crossing 滹沱桥, you fight the bridge
battle. (3) **Sight and discovery**: sight 3 (+1 on hills); parties and hidden
lairs are spotted by proximity — 黑风寨 starts unmarked on the map and renders as
unremarkable ground until found; `raze()` on a stormed lair disbands its band
for good. (4) **Provisions**: PROVISIONS_MAX=12 days of supplies, 1/day, refill
overnight at any settlement; at 0 the `starving` event fires (mood/desertion
arrive with M2). (5) All world randomness draws from the **"worldgen" stream**
— the first second-stream consumer, with a new test pinning that overworld play
can never perturb combat rolls (closes audit gap G16). 108 tests green.

**v0.27 (2026-06-12)** — **overworld v0: the 河北南部 test region** (M2 track) +
**会战 removed**. (1) **The strategic map is HEX**, same pointy-top axial grid and
(col,row)→q convention as the battle maps — settled over the proposed square grid
because the locked hex math is shared, there is no diagonal-distance distortion,
and the Godot port path is identical. One overworld hex ≈ half a 驿程;
MOVE_PER_DAY=8 points: 官道 1/hex · plain 2 · hills/forest 3 · rivers impassable
except 渡口 2 / 桥 1 (`sim/overworld.py`, `world/<region>.json`). (2) **The whole
map will follow the historical macro-regions** — 河北 · 河东 · 河南 · 关中 · 山东,
southern kingdoms as borders; first authored region: **河北南部, 24×16** (c. 942
后晋): the **拒马河 frontier** with 瀛州/莫州 beyond it as Liao-occupied towns
(幽云十六州, ceded 938 — M4 hooks), 镇州 (成德) / 定州 (义武) / 沧州 (横海) as the
garrison cities, 深州·河间·赵州·望都, the 滹沱河 with 滹沱桥 at 镇州's gates (守桥's
bridge), and 黑风寨 in the 西山 foothills (the battle scenarios' bandit lair on the
map). (3) Headless like M0: load → Dijkstra travel → day clock → travel events;
ASCII render; 7 tests (roads beat open country, rivers block except crossings,
frontier crossable only at the fords, all settlements reachable; 镇州→定州 = 2 天).
(4) **会战 · 黑风岭下 removed** as duplicative of 血战 (守桥 covers rout cascades,
血战 covers the big-map war); the 悍匪 templates retired with it; ladder back to
five. 100 tests green.

**v0.26 (2026-06-12)** — **血战 · 拒马河: the Khitan meat grinder** (endgame scenario
six, ★★★★★★ — the invasion-climax battle, fought at the historical anti-Khitan
river line). (1) **The Khitan column, within M0 mechanics**: cavalry stays M4; this
is the dismounted 打草谷 column — 12 new templates: 耶律详稳 (leader, iron, 精品
saber) · 皮室 iron guard ×4 (铁甲+铁盔 in 良品, two 长枪, one 大斧, one **骨朵 ≈
大锤** — the Khitan signature mace brings 碎甲 to BOTH sides) · 射雕手 ×2 · Han
auxiliary spear-and-crossbow infantry ×5 (the §1.x composition, reusing human AI).
(2) **Both sides graded to the teeth**: first fielding of **珍品 (zhen)** — 王铁枪's
famous 珍品·长枪, 刘三刀's 珍品·腰刀 (scenario override finally beating a template
quality), zhen mail on the front rank and the levies; the column in raw-to-良品
iron. (3) **Terrain: a 1-hex river** — impassable but reach-2 spears fight ACROSS
it and arrows fly over; two fords (the road ford north, mud ford south) are the
grinder lanes. (4) **Tuning lessons again formation-first**: levies in the front
rank → 0-2% player; 何九鞭 anchoring the south ford alone → he dies first in
79/100 seeds to 耶律详稳 personally (probe), igniting the cascade. Iron anchors
(石敢当/周大刀) at the fords + the whip as a second-rank counter-puncher + 燕小乙
on the north rise swung 2% → 58%; restoring the 皮室's 良品 lamellar landed it at
**50.8% player over 500 seeds** — dead even, mean 12.9 rounds, max 40, zero draws.
(5) **It IS a grinder, measured**: armor damage outpaces HP damage **1.72 : 1**
(field battles run well below 1); 碎甲 460 / 瞄准 3280 / 兜头 111 / 横扫 20 /
spearwall thrusts 202 per 200 battles. Ladder: 劫镖 60 · 守桥 56 · 对决 47 ·
攻寨 51 · 会战 56 · 血战 51. 94 tests green.

**v0.25 (2026-06-12)** — **会战 · 黑风岭下: the pitched battle** (the BB line-battle
fantasy, scenario five, ★★★★★). (1) First non-13×9 map — **17×11 open field**: an
east-west road, a north hill worth taking, bamboo cover on the south flank, a marsh
pond splitting the center. (2) **Largest engagement: 12 vs 17 (29 units)** — the
bureau's full muster plus four hired 乡勇 levies (new player templates: 2× 长枪
spearwall, 2× 短矛+盾) against the combined host of BOTH camps (坐山雕 + 过山风
fielded together — double leader-death ripples) reinforced by five new 悍匪 veteran
templates (2× 长枪, 砍刀+盾, 短矛+盾, 猎弓). (3) **Formation is the tuning lever
that mattered**: with mooks in the host's front rank the player won 76-96% — a probe
showed the first death was a resolve-30 喽啰 sniped by aimed archers at round ~2.3
in 95/100 seeds, igniting the rout cascade; moving armored veterans (精品 皮甲) to
the front rank and the mook reserve out of bow reach swung the battle 18 points by
itself. Final: 55.7% player over 300 seeds (53.4% over 500), mean 12.3 rounds.
(4) First scenario exercising **helmet_q** (过山风) and quality overrides at scale
(良品/精品 across the host's regulars). Ladder now: 劫镖 60 · 守桥 56 · 对决 47 ·
攻寨 51 · 会战 56. 93 tests green.

**v0.24 (2026-06-12)** — **combat-specials rework + the round-swing line** (both
implementations; ruleset changes, batch-verified). (1) **碎甲 demolish reworked**: was
pure armor damage with zero HP; now armor damage = min(armor present, dmg ×3), then
**blunt trauma through the remaining armor** — HP = max(0, dmg × pierce − 0.1 ×
(armor_before − armor_dmg)) — no head multiplier, no overflow channel (§3.10). The
maul now hurts the man inside the can it's opening. (2) **兜头 headhunt is now the
gamble swing**: the forced head hit lands at **×2.0** (was the generic ×1.5) but at
**−15 accuracy**, and a whiff **overswings for 15 extra Breath** — a full turn's
recovery thrown away, initiative sinking with it. High feedback, high risk, all
self-contained. Data-driven `head_mult`/`acc`/`miss_br` on the special dict; the
damage formula stays generic. (3) **横扫 now
has three carriers**: 大斧 (unchanged) plus two new weapons — **戟** (2H polearm,
reach 2, acc 12, 22–32, pierce 0.35, 坠气 5: reach *and* the round swing) and
**大关刀** (2H heavy blade, acc 8, 28–42, armor_eff 1.2, chop ×2.25 + bleed + 横扫,
坠气 6). Sweep still strikes the adjacent ring only. (4) **Two roster units** carry
them, fielded in 攻寨 only: 周大刀 (player, 大关刀, hp 60 / skill 58 / breath 90,
attacker spawn) and 钻山豹 (enemy, 戟, hp 54 / skill 55 / breath 88, garrisoned
defender) → 攻寨 is 6v8. (5) **AI v0 learns the new verbs**: 碎甲 fires on the first
target with body armor ≥50; 兜头 on the first with head armor ≤15, gated on ≥50%
base chance (§7). (6) **Morale
log now carries the full breakdown** — both engines emit base 胆识 / +3×adjacent
allies / situational mod on every morale event; §3.5's "log shows every modifier" is
now implemented, not aspirational. (7) **JS-parity fixes in the sim**: simultaneous
both-sides-zero elimination resolves to PLAYER (checkEnd tests the enemy side first);
load_scenario rejects duplicate unit ids (matching boot()). (8) **Balance after the
rework** (300 seeds each, AI vs AI): 劫镖 60% · 守桥 56% · 对决 47% · **攻寨 51%
player (was 40.7%)** — the 兜头 whiff tax prices the whip back to fair, landing the
siege at even and 对决 back on its pre-rework step. (9) Doc-honesty pass:
§3.1/§3.3–§3.10/§4.5/§7 aligned to code —
M0 modifier list enumerated (long thrust, falloff, special acc, flail shield-ignore,
举盾), surround documented attacker-side, up-front move cost, rout/rally numerics,
bleed numerics, drain-replaces-baseline, impassable-river vs future paddy, ammo and
line-of-fire deferrals, MAX_ROUNDS=100 harness draw cap, AI v0 spec rewritten to
match ai.py. 92 tests green.

**v0.23 (2026-06-12)** — **坠气, the carry tax** (canonical spec; equipment "weight"
abolished). (1) **Rename and generalize**: the armor `weight` field and the §3.11
quality multiplier column are now `br_tax`, displayed **坠气** — everything an escort
straps on drags on his wind — deliberately distinct from the per-strike 气力 cost
(`br`), which is untouched. Armor taxes keep the old weight values (布甲 3 … 铁甲 16).
(2) **Weapons now tax too** — every family declares 坠气 by heft (匕首 1 · 腰刀 2 ·
弩/长枪 4 · 大斧 5 · 大锤 6), and **max Breath = breath_base − 坠气 of body + helmet +
weapon + sidearm** (§3.1): BB's carry-fatigue made diegetic. The bagged sidearm is
paid all battle, sheathed or drawn; 换械 recomputes nothing. (3) **Quality lightens
weapons as well as armor**: the 坠气 multiplier (×1.00–0.85) now applies to weapon
taxes through the existing two-step rounding (q_round/qRound) — 刘三刀's 精品·腰刀
hangs at q_round(2×0.95) = 2. Per-strike br, AP, damage handling, pierce, armor-eff,
specials: unchanged. (4) **Cross-engine parity fixes** from review: quality override
resolution is nullish in both engines — a grade key *present* with `""` (or any
invalid id) fails loud, only an absent key (or JSON null) falls back
scenario → template → 凡品 (Python's truthy `or` chain replaced with explicit None
checks; JS `??` was already right); and all four grade slots (`wpn_q`/`wpn2_q`/
`armor_q`/`helmet_q`) validate eagerly in both engines — an invalid `wpn2_q` throws
even on a unit carrying no second weapon (game.js hoisted the resolution out of
`if (u.wpn2)`; Python was already eager). (5) **Ladder re-pinned** under the new tax,
batch-retuned and verified at 2000 seeds each: 劫镖 ★ 63.9% · 守桥 ★★ 54.9% ·
对决 ★★★ 47.7% · 攻寨 ★★★★ 40.7% — two quality-knob turns restore the v0.21 steps
(对决's 坐山雕 showcase trimmed to 良品 armor only, the living scenario-override
example; 劫镖's 夜猫子 gains a 良品·猎弓 mirroring 燕小乙's).

**v0.22 (2026-06-12)** — **equipment quality grades 品阶** (canonical spec; new §3.11).
(1) **Five grades, orthogonal to item identity** — 凡品 white · 良品 green · 精品 blue ·
珍品 purple · 神品 orange: damage ×1.00–1.50 + accuracy +0–10 on weapons, protection
×1.00–1.75 with weight ×1.00–0.85 on armor/helmets (high grades protect like iron, tax
Breath like leather — the BB famed-armor trade). Principle pinned: **quality buys
numbers, family buys verbs** — AP, Breath cost, reach, hands, pierce, armor-eff, and
specials are quality-immune. (2) **Wiring**: one QUALITY registry per implementation;
optional `wpn_q`/`wpn2_q`/`armor_q`/`helmet_q` (default 凡品) on roster templates *and*
scenario JSON units, scenario overriding template (the battle-test knob); quality
applies at unit creation to a deep copy, base tables never mutate; unknown grade ids
fail loud. (3) **Content**: the ad-hoc yaodao_fine/liegong_crude variants retired —
刘三刀 carries 腰刀 at 精品 (22–31, acc 14, 精品·腰刀), 猎弓 rebased to 14–24 凡品
(夜猫子 unchanged in numbers) with 燕小乙 at 良品 (15–26, acc 12, 良品·猎弓); 对决's
坐山雕 gets the showcase 良品 loadout (九环刀 26–37 acc 12, 铁甲 护 127, 铁盔 护 92,
weights unchanged so breath stays 68). §3.2 amended: tier table = 凡品 base values;
named armors (山文甲) and named blades are the 神品 layer (F4 famed gear, §5.3
loot-resell top rung). 82 tests green.

**v0.21 (2026-06-11)** — **stepwise difficulty ladder + full-folder problem scan**
(user direction). (1) **The ladder is now real steps**, batch-retuned and verified at
2000 seeds each: 劫镖 ★ 63% · 守桥 ★★ 57% · 对决 ★★★ 48% · 攻寨 ★★★★ 41% (was
58/57/57/46 with three scenarios tied). 劫镖: 坐山雕 no longer appears at his own
ambush — 蛇矛子 leads it with two 喽啰 added (4v7 of lighter troops; the chief stays
on his summit for the finale). 对决: a second road-pacing 跟班 (llb) joins the 三煞
→ 3v5. 攻寨: two garrisoned reinforcements inside the walls (喽啰 at the west gate,
二麻子 on the summit). 守桥: an uncommitted, overtuned two-column-river rework
(95% player) was stashed; the documented 57.5% version stands. Ruleset freeze held —
every change is scenario data. (2) **Scan fixes** (35-finding multi-agent audit,
adversarially verified): 围攻 no longer applies to friendly fire in either engine
(§3.6 was right, both implementations were wrong — reachable via 大斧 sweep);
web: 举盾/枪林/换械 now refresh the cached movement range (AP could go negative);
victory text no longer assumes a 4-man roster; both loaders validate scenario unit
ids; off-map road hexes no longer crash the web renderer; head-crit log/hover show
real per-weapon thresholds; spearwall messages use the weapon's own stance label
(枪阵 vs 枪林); sim runs on Python 3.9 again (`from __future__ import annotations`);
dead code removed (flat_scenario, unused imports, duplicate flee branch).
(3) **The standalone is now a build artifact**: tools/build_standalone.py regenerates
shattered_jade_battle.html from index.html + game.js + scenarios/*.json, and a parity
test fails the suite if it drifts — the third hand-synced rule copy is gone. pytest.ini
anchors rootdir; scenario JSONs normalized to one schema (all terrain layers explicit,
no elev-layer overlaps); structural tests now glob every scenario file. Doc honesty
pass: M0 deferrals recorded (vision, scatter, ordered Withdraw — §3.1/§3.8/§7.1
amended to match code), header version now tracks the changelog. 76 tests green.

**v0.20 (2026-06-11)** — **two new scenarios** (user direction: more difficulty
variety, exercise more of the mechanism space), both batch-tuned into the 50–60%
band. **守桥 ★★** (Hold the Bridge): outnumbered 4v9 river defense — new impassable
water terrain, one stone bridge + one ford (river topology pinned by BFS test),
garrisoned defenders, and a routable mook horde (four new 喽啰 templates, resolve 30,
plus bandit chief 过山风) — the morale-cascade and chokepoint showcase. Tuning note:
with a defending archer the chokehold measured 94–98% attacker-proof; the bow was
removed and 笑面虎 joined the pursuers → 57.5%/600 seeds. **对决 ★★** (The Showdown):
elite 3v4 on open ground around one hill — the pure weapon-matchup test (reach spear
vs shield-and-saber vs shield-ignoring flail vs greataxe); tuned from 70.6% by adding
a 跟班 to the 三煞 → 56.8%. Scenario dropdown is now a difficulty ladder:
劫镖 ★ 58% · 守桥 ★★ 57% · 对决 ★★ 57% · 攻寨 ★★★ 46%. Ruleset freeze held: all
additions are data (templates, terrain skin, scenarios). 70 tests green.

**v0.19 (2026-06-11)** — four approved improvements shipped. (1) **Version control**:
repo initialized and pushed to github.com/zhaoleli2025/Shattered_jade (commits per
feature from here on). (2) **Garrison AI rule** (both implementations): scenario JSON
units take `"garrison": N` — the AI holds within N hexes of its post while still
fighting anything in reach; all five 攻寨 defenders garrisoned, so the village finally
defends itself. (3) **攻寨 tuned by experiment**: entrenched baseline measured 12.6%
attacker; four lever combinations batch-tested; adopted variant D — 燕小乙 joins (5
attackers), 正门 widened to two hexes, 夜猫子 down to village ground (坐山雕 alone on
the 峰) — landing **45.8% over 800 seeds** (target 40–50; sieges now run ~16 rounds).
Combat ruleset is now **frozen pending M1** — no new rules, tuning only. (4)
**Battle-end summary screen**: per-unit damage/kills/fate (存活/溃走/阵亡) and battle
length on the victory/defeat overlay. HUD finalized BB-style: unit card bottom-left,
skill bar bottom-center, side panel = 行动顺序/命中推演/战斗记录. 69 tests green.

**v0.18 (2026-06-11)** — 攻寨 rebuilt as a **true mountain village** (user direction):
four elevation layers (valley 0 → slopes 丘 1 → village ground 岭 2 → summit 峰 3,
BB's full tier ladder; elev3 supported in scenario JSON, sim, and renderer), and the
walls now form a **village enclosure** — 8 wall hexes ringing a 4-hex interior with
exactly two entrances (正门 west, held by 蛇矛子; 后门 south), pinned by test. The
chief and archer hold the 峰 summit (archer range 10 from up there). UI: side panel
trimmed to exactly four sections (行动顺序 / 当前单位 / 命中推演 / 战斗记录) — help
text removed, unit inspection (right-click) merged into the 命中推演 panel. Baseline
shifted hard: 攻寨 now **31/69** (was 43/57) — three layers of uphill penalties plus
a two-gate funnel is brutal; tuning levers if it overshoots in play: widen 正门 to two
hexes, demote yemao off the summit, or stage attacker reinforcements. 68 tests green;
standalone rebuilt.

**v0.17 (2026-06-11)** — **armor tier system** (user direction): cloth/leather/iron
(布/皮/铁) for body and helmet as a data registry in both implementations; units now
carry a raw stamina stat (breath_base) and equipped armor weight is subtracted to give
max Breath — protection bought with stamina, per BB. All 13 units snapped to tier
loadouts (石敢当 and 坐山雕 full iron at −23 Breath; archers in cloth; the inspect
panel now names the armor and shows the weight math). Re-baselined: 劫镖 58/42
(was 74/26 — wang's custom 80/60 armor became leather, bandits gained cloth/leather
pieces; the closer fight is arguably the better baseline), 攻寨 43/57 (defenders'
tier snap favored them; tuning levers: 蛇矛子 back to cloth, or gate width). 68 tests
green including tier ordering and weight-tax computation.

**v0.16 (2026-06-11)** — walls + the second weapon modality (user direction), in both
implementations with parity. **Walls (寨墙/栅)**: impassable terrain hexes in scenario
JSON; 攻寨's fort is now ringed by a 6-hex palisade with the summit reachable only
through a 3-hex southwest gate (pinned by test). **New weapons**: 九节鞭 flail
(ignores the shield's base defense — raised-shield extra still counts, per BB; +10%
head chance; special 兜头 = forced head hit), 弩 crossbow (acc +15, armor-piercing
pierce 0.5, range 6), 短矛 1H spear (shield-compatible 枪阵 spearwall). New units:
陈短矛/何九鞭/鲁大弩 (assault specialists) + 蛇矛子 (defender with the 2H long spear).
**AI rule added (both)**: spear-bearers set the spearwall when enemies close to 2–3
hexes — the gate guard now actually guards. Batch (500): the specialist kit beats the
walls — 攻寨 54/46 player (was 40/60 with the road roster), mean 10.2 rounds (siege
pacing); crossbow 31 dmg/hit validates armor-piercing; the flail's shield-ignore is
why the chief now dies 44% (was 29%). 65 tests green.

**v0.15 (2026-06-11)** — **scenario system: battles are data.** New top-level
`scenarios/` holds one JSON per battle (map: road/cart/forest/elevations + unit
spawns + intro text), read by BOTH the browser prototype (fetch + header dropdown,
`?scenario=` param) and the sim (`load_scenario()`, `run_batch N <id>`). Unit
templates keep stable IDs in one registry per implementation; spawns moved out of
templates into scenarios. Second battle shipped: **攻寨 (storm the hill fort)** —
the player attacks uphill into the chief and archer holding the elev-2 summit.
Batch data proves the terrain rules carry the design: 劫镖 74/26 player vs 攻寨
40/60 — same units, same rules, the hill alone flips the matchup; the hilltop
archer's death rate drops 69%→29%. Known AI limit (documented): defenders descend
to engage rather than holding the summit — a "hold position" behavior is an M3 AI
item. 58 tests green (scenario-validation tests added).

**v0.14 (2026-06-11)** — **M0 shipped: the pure-Python combat sim** (`sim/`, ~1,400
lines + 56 tests). Engine-agnostic core per §7: data-driven content with stable IDs,
named seeded RNG streams, command-pattern resolution (Move/Strike/Stance/Swap — the
skill-bar vocabulary), dual-budget pathfinding in the core, v0 AI, ASCII view, and an
AI-vs-AI batch runner (~340 battles/sec). **Verification** (3-agent panel): parity
audit vs the prototype found the port bit-identical on the damage model (691k
enumerated cases), hit formula (5k cases), pathfinding (400 setups), and all
stats/AI thresholds — one real divergence fixed (ZoC: all adjacent strikers swing
before a hit cancels the move) plus three latent ones; a 12,000-battle fuzz passed
with zero crashes/invariant violations and byte-identical replays per seed; the
test-adequacy review's 17 gap tests were all added (bleed, routs, rallies, escapes,
upkeep, initiative, AI hand rules — via a scripted FakeRNG). One shared AI hole fixed
in BOTH implementations: out-of-range archers now advance (was: mutual stand-off →
forced draws). First balance data (1,000 ambush battles): player 70.1%, mean 7.7
rounds, 0 draws; flat-map matchup batches documented as needing both-orientation
averaging (hex mirror asymmetry). **M0 exit criterion met: rules sound, schema
locked.** Next: M1 (Godot vertical slice).

**v0.13 (2026-06-11)** — **BB-style skill bar** (user direction): the active unit's
actions now live in a bar at the bottom of the battlefield, exactly as in Battle
Brothers — named basic attack (刺击/劈砍/锤击/重劈/放箭), weapon special, 举盾, 换械,
结束, each with costs on the button. Exactly one skill is selected (gold); **clicking
ground always moves, clicking a target uses the selected skill**; stances (枪林)
execute instantly; selection reverts to the basic attack after a special and on weapon
switch. Replaces the unit-card arm-toggle from v0.11.

**v0.12 (2026-06-11)** — **title final: Shattered Jade (碎玉)** (user's pick — drops
the 行 of 碎玉行; English follows the Chinese). Folder decluttered at user direction:
nine research digests consolidated into one `RESEARCH.md`; `reviews/` (incorporated at
v0.2), `prototype_web/fonts/` (8.5 MB rolled-back Zhuque TTF), and the regenerable
standalone HTML removed. The project is now four files: `DESIGN.md`, `RESEARCH.md`,
`prototype_web/index.html`, `prototype_web/game.js` (268 KB total).

**v0.11 (2026-06-11)** — **every weapon family gains its BB signature skill** (user
direction), live in the prototype: 枪 **枪林 Spearwall** (stance, 3 AP/18 Breath:
approaching enemies eat a half-damage thrust, a hit halts them — BB's
movement-stopping spearwall); 刀 family **斩首 Decapitate** (5/15, ×1.3 damage, kills
terrify: nearby enemies check at −10); 大锤 **碎甲 Demolish Armor** (6/20, armor ×3,
zero HP); 大斧 **横扫 Round Swing** (6/20, hits ALL adjacent, friend and foe, −10 acc);
弓 **瞄准 Aimed Shot** (6/12, +10 acc, falloff halved). UI: arm-then-click special
buttons (gold when armed); 枪/盾 stance badges. AI uses all of them by family rule
(decap executes the wounded, sweep only with ≥2 foes and no friends adjacent, aimed
on low-chance shots). Adversarial re-review of the new code paths found 6 issues —
including a head-hit crash that would have soft-locked 1 in 4 hits — all fixed
(fleeing spearwallers disarmed, stale armed-state UI, stance cleared on weapon switch,
log tag precedence).

**v0.10 (2026-06-11)** — four user directions: (1) **bows/crossbows minimum range 2**
(no point-blank shots; closing on archers is now a tactic, §3.7); (2) **weapon
switching, 4 AP** (§3.1) — prototype: 燕小乙 carries a 匕首 sidearm (Puncture: 100%
armor-pierce, no headshots), 王铁枪 a backup 腰刀, the bandit archer a 短刀, and the AI
draws steel when pinned; (3) **棍 staff deleted** from the arsenal (monk background
reflavored); (4) **Raise Shield 举盾** (BB Shieldwall: 4 AP + 10 Breath, shield bonus
×2 until next turn, §3.10) — both player UI button and AI rule (out-of-attacks
shield-bearers raise against adjacent foes).

**v0.9 (2026-06-11)** — 2H weapons given their BB parameter premium (user direction):
each two-handed weapon buys ONE axis at ~2× the 1H number — **reach** (枪/关刀),
**damage + head-hunting** (斩马刀/大斧/大刀), or **armor destruction + Breath drain**
(大锤/狼牙棒) — codified in §3.10 with the damage and armor lines as table rows.
Prototype: 石敢当 → 2H 大锤 (28–40, armor eff ×2, +20 Breath drain, 6 AP — strips the
chief's 110 armor in 2 swings and fatigue-locks him by the 3rd, verified by math
trace); 笑面虎 → 2H 大斧 (30–44, 爆头 ×2.25 — the enemy-side terror weapon).

**v0.8 (2026-06-11)** — weapon grip system made explicit, BB-faithful (user direction):
1H weapons pair with shields or double-grip (+25% damage, empty off-hand); 2H weapons
forbid shields, 6 AP per strike. **枪 long spear is two-handed with 2-hex reach**
(long thrust −15 acc unless mastered; 短矛 short spear noted as the 1H+shield variant).
Prototype: 王铁枪 → 2H reach spear in the second rank; 刘三刀 → 刀盾 (saber + rattan
shield) point-man; 石敢当 and the bandit 砍刀/斧 fighters now double-grip (damage
rebalanced down so effective output stays level). Input split: **left click = move/
attack only, right click = inspect** (was: left click did both).

**v0.7 (2026-06-11)** — **roads on the battlefield** (user direction): road hexes cost
normal AP but half Breath (1 vs 2/hex), added to §3.1; escort-ambush (劫镖) battles
seed the road + impassable convoy cart 镖车 across the map (§5.6). Prototype scenario
rebuilt as a true 劫镖: mountain road bending around the hill, cart on the road,
escorts deployed around the cargo, bandits attacking from the road ahead, the hilltop,
the hillside, and the forest flank. Pathfinding now tracks AP and Breath as separate
budgets; move preview shows exact Breath cost and flags road-only routes (省力).

**v0.6.1 (2026-06-11)** — font verdict from play: 朱雀仿宋 rolled back to
document-screens-only; **LXGW WenKai restored as primary UI font**. Prototype QoL:
Enter/Return ends the turn; every unit now carries three bars — HP, body armor
(steel blue), helmet (bronze) — armor bars drawn as a fraction of starting armor so
degradation is visible at a glance.

**v0.6 (2026-06-11)** — Chinese title finalized: **碎玉行** (*Ballad of the Shattered
Jade* — 宁为玉碎 permadeath creed + 行 ballad/road double meaning), chosen by the user
over 玉碎天命/玉玺无主/玉与天命. Lost-Seal lore anchor added (传国玉玺 vanished 937 →
F4 legendary artifact). Typography: **朱雀仿宋 promoted to primary UI font** (user's
pick; self-hosted in the prototype), WenKai demoted to fallback. Prototype: click any
unit (or right-click) to **inspect** — full panel with weapon stats (damage, 破甲/穿甲,
costs), armor pools, traits, morale, current initiative.

**v0.5 (2026-06-11)** — **title decided: Jade & Destiny (玉与天命)**, replacing the
working title Blood & Silver (jade ties to the 玉 trade good and the escorted cargo;
天命 to the era's contested Mandate). §6 gains a typography spec: LXGW WenKai (body) ·
KingHwa OldSong (display) · Noto Sans SC (dense UI) · Zhuque Fangsong (documents), all
OFL/free-commercial; system CJK fonts (方正/汉仪/华文/SimSun) banned for licensing.
Prototype retitled and switched to LXGW WenKai via CDN.

**v0.4.1 (2026-06-11)** — hit model locked after discussion: **single d100 under
chance, modifiers staged by milestone** (§3.3) — M0/M1 ships only accuracy + height +
surround + simple morale; alternatives considered and rejected: d20 steps (same math,
coarser perk space), 2d6 bell curve (opaque odds, nonlinear modifier balance),
always-hit/damage-variance (deletes defense builds and the miracle/tragedy register —
the Wartales trade).

**v0.4 (2026-06-11)** — company identity generalized; modular anatomy made explicit
(both at the user's direction).

- §1: the player leads a **free company**, not necessarily a bureau — the unseen
  master's title varies by origin (总镖头 / captain / chief); pillar 1 reworded
  ("the company is the protagonist"). The soldier's path is first-class: §5.6 adds
  **military contracts (军务)** from the provincial courts (the BB noble-contract
  analog — pitched battles, sieges, supply raids; open to any company), and §5.9 adds
  the **Broken Garrison 残旗溃卒** origin (ex-provincial soldiers; military contracts
  from day one; rival commander instead of rival bureau). v1 origins = 3.
- §4.5 (new): **modular anatomy** — BB's paper-doll confirmed as a formal structure:
  mechanical slots (head / body / main hand / off hand / ammo / accessory) and visual
  bust layers keyed to the same item IDs; one JSON entity per item carries stats,
  weight, durability, and sprite layer. Scar overlays; visible helmet/Vision tradeoff.
  Roster/bench renumbered to §4.6.

**v0.3 (2026-06-11)** — era re-anchored at the user's direction: **Five Dynasties
(c. 907–960) with the Khitan (Liao) invasion as every campaign's essential climax.**

- §2.1 rewritten: 藩镇/节度使 powers (era-native — the v0.1 reviewer's option (a)),
  牙兵/义儿/Shatuo era texture, copper-cash economy, 镖局 anachronism stated honestly,
  An Chongrong epigraph, and a reference shelf (新五代史/资治通鉴/伶官传序; 残唐五代史演义,
  十三太保, 杨家将, 天龙八部; 刺客聂隐娘, 满城尽带黄金甲). Historical claims verified by a
  fact-check agent (one fix: The Assassin is mid-Tang; quote variant 邪).
- §2.2: Black Banner replaced by the **Khitan Empire as a rival state** — disciplined
  cavalry + Han auxiliaries + 打草谷 columns, never an ethnic horde; sensitivity
  principle adapted (杨家将/天龙八部 precedent, 契丹逃卒 sympathetic background, Shatuo
  blurriness noted); Northern Marches (燕云十六州 model) added to the map.
- §2.3 restructured: **one essential crisis** (契丹南下, built from the 936 石敬瑭
  cession + 946–947 occupation-and-withdrawal arc, with the collaborator-jiedushi
  trigger and three resolutions) + two variable pre-invasion crises (post-v1). v1's
  shipped crisis is now the invasion; Pure Lotus moves post-v1.
- §4.2: 伶人 replaces 戏班武生 (era-correct, 伶官传序 hooks); added 契丹逃卒 and 牙兵
  backgrounds. §4.4: 义儿/oath era-resonance noted. §5.1: 军镇/戍堡, 藩镇, Marches
  region. §5.3: currency defined. §5.6: frontier contract templates. §7.1 M4: invasion
  faction scoped (auxiliary infantry + one cavalry archetype; kiting post-v1).
  §9: Q9 (Khitan-side playability), Q10 (naming asymmetry) added.

**v0.2 (2026-06-11)** — incorporates the 53-finding adversarial review
(`reviews/review-v0.1.json`; 4 lenses: systems coherence, wuxia authenticity, scope
realism, completeness vs research). Headline changes:

- *Systems*: F6 reveal capped (star map never purchasable); rival bureau re-clocked
  (parallel, never inverse — no kick-while-down) and finale made asymmetric; endgame
  ladder given player-side fuel (famed gear + capped manuals + legendary sites) and a
  scaling ceiling; F9 pays fame not XP (protects scaling/wage calibration); Xia middle
  de-penalized; twist tables split flavor/difficulty with bounds; pay formula
  disambiguated (roster strength never enters pay); transparency principle stated
  (combat exact / social fuzzy-but-signaled); morale-log spec; economy KPI added.
- *Wuxia*: 胡骑 → Black Banner (occupational, not ethnic); White Lotus → fictional
  Pure Lotus 净莲教 (gloss 妖教); mounted-combat contradiction resolved (horse+rider
  unit archetype); Ming anchor (总兵/军门); terminology sweep (仵作=coroner, 还俗僧/落魄道士
  glosses fixed, 戏班武生, 武馆, 九节鞭, 暗器, 金疮药, 金盆洗手); supernatural kept at the
  edge (humans front-stage in the crisis); tone references fixed (Xu Haofeng, 老舍,
  王度庐 in; 卧虎藏龙 out); **added 喊镖号 trail-call parley and 结拜 sworn brotherhood**;
  player framed as 总镖头; Jin Yong IP content rule; 镖行天下 title struck.
- *Scope*: milestones re-cut with honest calendar ranges and exit criteria; M0 goal
  reframed ("schema locked," not "fun"); M1 juice closed-list + art-pipeline
  validation + kill/pivot checkpoint; M2 ruthless minimums; suspend save moved to M3;
  AI v0 defined; content quantities split slice/v1/post-v1; bilingual = externalize
  now, translate later.
- *Completeness*: added retreat (§3.8), vision (§3.4), ranged cover/scatter (§3.7),
  settlement situations (§5.2), F13 inventory/comparison UX, F14 onboarding, bench
  rules (§4.5), female recruits decision, retinue-followers conscious fold, authored-
  companions conscious cut, legendary sites, pathfinding-in-core and single-source-
  tooltip bullets (§7).

**v0.1 (2026-06-11)** — initial draft from the 9-stream Battle Brothers research.
