"""Content data — weapons, unit templates, scenario maps.

Stable string IDs throughout (DESIGN.md §7 data-driven rule). Values mirror
prototype_web/game.js exactly; that file is the reference implementation.
"""

# ---- quality grades (品阶): quality buys numbers, family buys verbs ----
# Applied at unit creation to a copy of the item; AP/Breath/reach/pierce/
# armor_eff/specials are quality-immune. Multipliers round via js_round.
# br_tax scales the 坠气 carry tax: graded gear is finer-made and lighter.
QUALITY = {
    "fan": dict(id="fan", label="凡品", color="#9b9b9b", rank=0,
                dmg=1.00, acc=0, protect=1.00, br_tax=1.00),
    "liang": dict(id="liang", label="良品", color="#3f8f4a", rank=1,
                  dmg=1.10, acc=2, protect=1.15, br_tax=1.00),
    "jing": dict(id="jing", label="精品", color="#3873b8", rank=2,
                 dmg=1.20, acc=4, protect=1.30, br_tax=0.95),
    "zhen": dict(id="zhen", label="珍品", color="#8a4bb0", rank=3,
                 dmg=1.35, acc=7, protect=1.50, br_tax=0.90),
    "shen": dict(id="shen", label="神品", color="#d2691e", rank=4,
                 dmg=1.50, acc=10, protect=1.75, br_tax=0.85),
}

# ---- weapons (special: spearwall=stance, decap/demolish/aimed/sweep=strikes) ----
# br_tax is the 坠气 carry tax: subtracted from breath_base while the weapon
# is carried (sidearms too, even sheathed) — distinct from per-strike br.
WEAPONS = {
    "changqiang": dict(  # 长枪 — 2H reach line
        id="changqiang", label="长枪", kind="melee", hands=2, reach=2, acc=20,
        dmin=22, dmax=32, armor_eff=0.9, pierce=0.30, ap=6, br=15, br_tax=4,
        special=dict(type="spearwall", label="枪林", ap=3, br=18)),
    "yaodao": dict(  # 腰刀 (王铁枪's backup; 刘三刀 carries a 精品)
        id="yaodao", label="腰刀", kind="melee", hands=1, acc=10,
        dmin=18, dmax=26, armor_eff=1.0, pierce=0.30, ap=4, br=12, br_tax=2,
        bleed=True,
        special=dict(type="decap", label="斩首", ap=5, br=15, dmg_mult=1.3)),
    "dachui": dict(  # 大锤 — 2H armor line
        id="dachui", label="大锤", kind="melee", hands=2, acc=5,
        dmin=28, dmax=40, armor_eff=2.0, pierce=0.20, ap=6, br=18, br_tax=6,
        breath_drain=20,
        special=dict(type="demolish", label="碎甲", ap=6, br=20, armor_mult=3.0)),
    "dafu": dict(  # 大斧 — 2H damage line
        id="dafu", label="大斧", kind="melee", hands=2, acc=5,
        dmin=30, dmax=44, armor_eff=1.3, pierce=0.25, ap=6, br=16, br_tax=5,
        chop=True,
        special=dict(type="sweep", label="横扫", ap=6, br=20, acc=-10)),
    "ji": dict(  # 戟 — 2H polearm: reach AND the round swing
        id="ji", label="戟", kind="melee", hands=2, reach=2, acc=12,
        dmin=22, dmax=32, armor_eff=1.0, pierce=0.35, ap=6, br=15, br_tax=5,
        special=dict(type="sweep", label="横扫", ap=6, br=20, acc=-10)),
    "daguandao": dict(  # 大关刀 — 2H heavy blade: the chopping round swing
        id="daguandao", label="大关刀", kind="melee", hands=2, acc=8,
        dmin=28, dmax=42, armor_eff=1.2, pierce=0.30, ap=6, br=17, br_tax=6,
        chop=True, bleed=True,
        special=dict(type="sweep", label="横扫", ap=6, br=20, acc=-10)),
    "liegong": dict(  # 猎弓 (凡品 = bandit grade; 燕小乙 carries a 良品)
        id="liegong", label="猎弓", kind="ranged", hands=2, acc=10,
        dmin=14, dmax=24, armor_eff=0.6, pierce=0.35, ap=4, br=8, br_tax=2,
        range=7, falloff=3,
        special=dict(type="aimed", label="瞄准", ap=6, br=12, acc_bonus=10, falloff=2)),
    "kandao": dict(  # 砍刀
        id="kandao", label="砍刀", kind="melee", hands=1, acc=10,
        dmin=17, dmax=26, armor_eff=1.0, pierce=0.30, ap=4, br=12, br_tax=2,
        bleed=True,
        special=dict(type="decap", label="斩首", ap=5, br=15, dmg_mult=1.3)),
    "jiuhuandao": dict(  # 九环刀 (leader)
        id="jiuhuandao", label="九环刀", kind="melee", hands=1, acc=10,
        dmin=24, dmax=34, armor_eff=1.0, pierce=0.30, ap=4, br=12, br_tax=3,
        bleed=True,
        special=dict(type="decap", label="斩首", ap=5, br=15, dmg_mult=1.3)),
    "bishou": dict(  # 匕首 — Puncture: full pierce, no armor damage, no headshots
        id="bishou", label="匕首", kind="melee", hands=1, acc=-15,
        dmin=14, dmax=22, armor_eff=0.0, pierce=1.0, ap=4, br=10, br_tax=1,
        no_head=True),
    "duanmao": dict(  # 短矛 — the 1H spear: shield-compatible spearwall
        id="duanmao", label="短矛", kind="melee", hands=1, acc=15,
        dmin=16, dmax=24, armor_eff=0.9, pierce=0.25, ap=4, br=11, br_tax=2,
        special=dict(type="spearwall", label="枪阵", ap=3, br=16)),
    "jiujiebian": dict(  # 九节鞭 — flail line: ignores shields, hunts heads
        id="jiujiebian", label="九节鞭", kind="melee", hands=1, acc=5,
        dmin=18, dmax=28, armor_eff=0.9, pierce=0.30, ap=4, br=13, br_tax=3,
        ignore_shield=True, head_bonus=10,
        # the gamble: forced head ×2.0, but −15 to land and a whiff overswings
        # for 15 extra Breath — a full turn's recovery thrown away
        special=dict(type="headhunt", label="兜头", ap=5, br=16, head_mult=2.0,
                     acc=-15, miss_br=15)),
    "nu": dict(  # 弩 — crossbow: flat power, armor-piercing, shorter range
        id="nu", label="弩", kind="ranged", hands=2, acc=15,
        dmin=22, dmax=32, armor_eff=0.8, pierce=0.50, ap=4, br=10, br_tax=4,
        range=6, falloff=2,
        special=dict(type="aimed", label="瞄准", ap=6, br=14, acc_bonus=10, falloff=1)),
    "duandao": dict(  # 短刀
        id="duandao", label="短刀", kind="melee", hands=1, acc=0,
        dmin=14, dmax=22, armor_eff=0.8, pierce=0.30, ap=4, br=10, br_tax=1),
}

# ---- armor tiers: protection is an ablative pool, br_tax (坠气) taxes max
# Breath — everything a man straps on drags on his wind, weapons included ----
ARMOR = {
    "none_b": dict(id="none_b", label="无甲", slot="body", protect=0, br_tax=0),
    "bujia": dict(id="bujia", label="布甲", slot="body", protect=25, br_tax=3),
    "pijia": dict(id="pijia", label="皮甲", slot="body", protect=60, br_tax=8),
    "tiejia": dict(id="tiejia", label="铁甲", slot="body", protect=110, br_tax=16),
    "none_h": dict(id="none_h", label="无盔", slot="head", protect=0, br_tax=0),
    "bumao": dict(id="bumao", label="布帽", slot="head", protect=15, br_tax=1),
    "pikui": dict(id="pikui", label="皮盔", slot="head", protect=40, br_tax=3),
    "tiekui": dict(id="tiekui", label="铁盔", slot="head", protect=80, br_tax=7),
}

# ---- unit templates (id, side, stats, weapon + armor ids) ----
# Spawns live in scenario files (scenarios/*.json), not here.
# Optional wpn_q/wpn2_q/armor_q/helmet_q pick a QUALITY grade (default 凡品);
# scenario unit entries may override them per battle.
# breath_base is the man's raw stamina; the 坠气 of armor, helmet, weapon AND
# carried sidearm is subtracted to give breath_max (the BB carry trade-off —
# a sheathed sidearm still drags; 换械 recomputes nothing).
ROSTER = [
    dict(id="wang", name="王铁枪", glyph="枪", side="player", hp_max=55, skill=62, dfn=10,
         shield=0, resolve=48, init_base=96, breath_base=87, armor="pijia", helmet="pikui",
         wpn="changqiang", wpn2="yaodao"),
    dict(id="liu", name="刘三刀", glyph="刀", side="player", hp_max=60, skill=60, dfn=6,
         shield=15, resolve=45, init_base=104, breath_base=87, armor="pijia", helmet="pikui",
         wpn="yaodao", wpn_q="jing", wpn2=None),
    dict(id="shi", name="石敢当", glyph="锤", side="player", hp_max=65, skill=58, dfn=5,
         shield=0, resolve=50, init_base=90, breath_base=93, armor="tiejia", helmet="tiekui",
         wpn="dachui", wpn2=None),
    dict(id="yan", name="燕小乙", glyph="弓", side="player", hp_max=45, skill=56, dfn=8,
         shield=0, resolve=42, init_base=112, breath_base=94, armor="bujia", helmet="bumao",
         wpn="liegong", wpn_q="liang", wpn2="bishou"),
    dict(id="duyan", name="独眼龙", glyph="刀", side="enemy", hp_max=50, skill=52, dfn=4,
         shield=0, resolve=38, init_base=100, breath_base=89, armor="bujia", helmet="bumao",
         wpn="kandao", wpn2=None),
    dict(id="erma", name="二麻子", glyph="刀", side="enemy", hp_max=50, skill=52, dfn=4,
         shield=0, resolve=38, init_base=98, breath_base=89, armor="bujia", helmet="bumao",
         wpn="kandao", wpn2=None),
    dict(id="xiaohu", name="笑面虎", glyph="斧", side="enemy", hp_max=55, skill=54, dfn=4,
         shield=0, resolve=40, init_base=94, breath_base=86, armor="bujia", helmet="pikui",
         wpn="dafu", wpn2=None),
    dict(id="yemao", name="夜猫子", glyph="弓", side="enemy", hp_max=42, skill=50, dfn=6,
         shield=0, resolve=36, init_base=108, breath_base=91, armor="bujia", helmet="none_h",
         wpn="liegong", wpn2="duandao"),
    dict(id="diao", name="坐山雕", glyph="首", side="enemy", hp_max=70, skill=62, dfn=12,
         shield=15, resolve=55, init_base=92, breath_base=91, armor="tiejia", helmet="tiekui",
         wpn="jiuhuandao", wpn2=None, leader=True),
    # ---- the assault specialists (攻寨 roster) ----
    dict(id="chen", name="陈短矛", glyph="矛", side="player", hp_max=58, skill=58, dfn=8,
         shield=15, resolve=46, init_base=100, breath_base=89, armor="pijia", helmet="pikui",
         wpn="duanmao", wpn2=None),
    dict(id="he", name="何九鞭", glyph="鞭", side="player", hp_max=52, skill=57, dfn=7,
         shield=0, resolve=44, init_base=106, breath_base=90, armor="bujia", helmet="pikui",
         wpn="jiujiebian", wpn2=None),
    dict(id="lu", name="鲁大弩", glyph="弩", side="player", hp_max=48, skill=54, dfn=6,
         shield=0, resolve=45, init_base=95, breath_base=89, armor="pijia", helmet="bumao",
         wpn="nu", wpn2="duandao"),
    dict(id="zhou", name="周大刀", glyph="关", side="player", hp_max=60, skill=58, dfn=6,
         shield=0, resolve=47, init_base=93, breath_base=90, armor="pijia", helmet="pikui",
         wpn="daguandao", wpn2=None),
    dict(id="shemao", name="蛇矛子", glyph="矛", side="enemy", hp_max=52, skill=55, dfn=6,
         shield=0, resolve=40, init_base=96, breath_base=89, armor="pijia", helmet="bumao",
         wpn="changqiang", wpn2=None),
    dict(id="zuanshan", name="钻山豹", glyph="戟", side="enemy", hp_max=54, skill=55, dfn=6,
         shield=0, resolve=41, init_base=97, breath_base=88, armor="pijia", helmet="bumao",
         wpn="ji", wpn2=None),
    # ---- the bridge mob (守桥 roster): brittle mooks that rout in cascades ----
    dict(id="lla", name="喽啰·甲", glyph="卒", side="enemy", hp_max=40, skill=46, dfn=3,
         shield=0, resolve=30, init_base=102, breath_base=85, armor="bujia", helmet="none_h",
         wpn="duandao", wpn2=None),
    dict(id="llb", name="喽啰·乙", glyph="卒", side="enemy", hp_max=40, skill=46, dfn=3,
         shield=0, resolve=30, init_base=101, breath_base=85, armor="bujia", helmet="none_h",
         wpn="duandao", wpn2=None),
    dict(id="llc", name="喽啰·丙", glyph="卒", side="enemy", hp_max=40, skill=46, dfn=3,
         shield=0, resolve=30, init_base=100, breath_base=85, armor="bujia", helmet="none_h",
         wpn="duandao", wpn2=None),
    dict(id="lld", name="喽啰·丁", glyph="卒", side="enemy", hp_max=40, skill=46, dfn=3,
         shield=0, resolve=30, init_base=99, breath_base=85, armor="bujia", helmet="none_h",
         wpn="duandao", wpn2=None),
    dict(id="guoshanfeng", name="过山风", glyph="首", side="enemy", hp_max=62, skill=58, dfn=9,
         shield=15, resolve=50, init_base=95, breath_base=88, armor="pijia", helmet="pikui",
         wpn="jiuhuandao", wpn2=None, leader=True),
]

COLS, ROWS = 13, 9  # BattleState defaults; real maps come from scenario JSON
