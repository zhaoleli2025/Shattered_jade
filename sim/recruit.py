"""Recruitment — BB-style procedural identity for hired hands (DESIGN §4.2–4.3).

A recruit is a named character: 姓+名 plus a Water Margin 绰号, a 出身
(background) that sets stat ranges / fee / wage / weapon, 0–2 hidden 特性
(traits) with real effects, and 3 hidden 天赋 (talent stars) that wait for the
leveling system. Generation is deterministic per (world seed, settlement, the
refreshing epoch), drawn from a dedicated Random so it never perturbs combat.

Graduated reveal (F6): a free LOOK shows the background and one hint; 茶馆
gossip reveals the traits; the 医馆 exam reveals the talent COUNT and one
attribute — the full star map is never purchasable, only level-ups show it.
"""
import random

# common 五代 surnames + given-name characters + Water Margin nicknames
SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦许何吕张孔曹"
                "高石马苗凤花方俞任袁柳鲍史唐费岑薛雷贺倪汤滕殷罗毕郝邬安常乐于")
GIVEN = list("勇刚虎彪豹龙彦荣贵福禄寿山林川河海江云风雷电铁钢锐锋利胜"
             "忠义信勇仁孝节烈雄威猛壮健安平定兴旺富贵金玉珠宝栋梁柱石根本")
FEMALE_GIVEN = list("娘秀英兰花玉珠香莲翠红梅杏桃春燕莺凤娥婵娟淑慧")
FEMALE_NICKS = {"母大虫", "母夜叉", "一丈青"}   # gendered 绰号 stay with the 女侠

NICKNAME = {
    "tianong": ["拼命三郎", "黑旋风", "病大虫", "笑面虎", "急先锋", "母大虫"],
    "tuihuo": ["丧门神", "催命判官", "翻江蜃", "白日鼠", "鼓上蚤", "短命二郎"],
    "liehu": ["小李广", "赛仁贵", "落地太岁", "花项虎", "射雕手", "穿云箭"],
    "huanseng": ["花和尚", "行者", "金刚", "降魔尊者", "铁罗汉", "醉头陀"],
    "tangzishou": ["神行太保", "镇三山", "插翅虎", "美髯公", "金枪手", "病关索"],
    "youxia": ["豹子头", "小旋风", "玉麒麟", "青面兽", "九纹龙", "扑天雕",
               "浪里白条", "一丈青", "双枪将"],
}

# ---- backgrounds (出身): stat ranges, price, wage, weapon, trait bias ----
# ranges are (lo, hi) inclusive; the roll is uniform; traits bias the pool.
BACKGROUNDS = {
    "tianong": dict(
        name="佃农", fee=(30, 50), wage=2, weapon="duanmao", shield=0,
        glyph="佃", armor="bujia", helmet="bumao",
        hp=(40, 48), skill=(44, 50), dfn=(3, 5), resolve=(32, 40),
        init=(92, 100), breath=(84, 92),
        traits=["jianzhuang", "lannuo", "tiefei"], blurb="田间出身，能扛能熬，假以时日未必不能成器"),
    "tuihuo": dict(
        name="退伙强人", fee=(40, 70), wage=3, weapon="kandao", shield=0,
        glyph="贼", armor="bujia", helmet="pikui",
        hp=(44, 52), skill=(48, 54), dfn=(4, 6), resolve=(36, 44),
        init=(96, 104), breath=(84, 90),
        traits=["tanlan", "jieao", "jiujiu", "hanyong"], blurb="刀头舔血过来的，手熟，心也野"),
    "liehu": dict(
        name="猎户", fee=(70, 100), wage=4, weapon="liegong", wpn2="duandao", shield=0,
        glyph="猎", armor="bujia", helmet="bumao",
        hp=(42, 48), skill=(50, 56), dfn=(5, 7), resolve=(38, 44),
        init=(104, 112), breath=(88, 94),
        traits=["duyan", "tiefei", "hanyong"], blurb="山林里讨生活，一手好箭法，眼也尖"),
    "huanseng": dict(
        name="还俗僧", fee=(90, 130), wage=5, weapon="dachui", shield=0,
        glyph="僧", armor="pijia", helmet="none_h",
        hp=(52, 62), skill=(50, 56), dfn=(5, 7), resolve=(48, 56),
        init=(88, 96), breath=(90, 96),
        traits=["shenli", "jiujiu", "hanyong"], blurb="酒肉穿肠的莽和尚，禅杖一抡，鬼神皆惊"),
    "tangzishou": dict(
        name="趟子手", fee=(100, 150), wage=5, weapon="yaodao", shield=15,
        glyph="镖", armor="pijia", helmet="pikui",
        hp=(50, 58), skill=(54, 60), dfn=(6, 9), resolve=(42, 48),
        init=(96, 104), breath=(87, 92),
        traits=["hanyong", "tiefei"], blurb="押过多少趟镖的老手，稳，可靠"),
    "youxia": dict(
        name="游侠", fee=(200, 300), wage=8, weapon="changqiang", shield=0,
        glyph="侠", armor="pijia", helmet="pikui",
        hp=(48, 58), skill=(60, 68), dfn=(8, 12), resolve=(44, 52),
        init=(104, 114), breath=(88, 94),
        traits=["shenli", "hanyong", "bozu"], blurb="来去无踪的剑客，价高，却也值这个价"),
}

# ---- traits (特性): each tweaks the rolled character ----
TRAITS = {
    "shenli": dict(name="天生神力", good=True, desc="兵器伤害 +3"),
    "tiefei": dict(name="铁肺", good=True, desc="气力 +12"),
    "hanyong": dict(name="悍勇", good=True, desc="胆识 +8"),
    "danqie": dict(name="胆怯", good=False, desc="胆识 −8"),
    "duyan": dict(name="独眼", good=False, desc="准头 −10"),
    "bozu": dict(name="跛足", good=False, desc="先手 −8"),
    "jiujiu": dict(name="嗜酒", good=False, desc="日饷 +1"),
    "tanlan": dict(name="贪婪", good=False, desc="日饷 +2"),
    "jieao": dict(name="桀骜", good=False, desc="胆识 −4，武艺 +4"),
    "jianzhuang": dict(name="健壮", good=True, desc="血 +6"),
    "lannuo": dict(name="懒惰", good=False, desc="先手 −4"),
}

ATTRS = ["hp", "skill", "dfn", "resolve", "init", "breath"]
ATTR_NAME = {"hp": "血", "skill": "武艺", "dfn": "招架", "resolve": "胆识",
             "init": "先手", "breath": "气力"}
REFRESH_DAYS = 6           # the pool turns over this often (BB: a few days)
POOL_SIZE = 4


def _pool_rng(world_seed, settlement_id, epoch):
    return random.Random(f"recruit:{world_seed}:{settlement_id}:{epoch}")


def _roll(rng, lo_hi):
    return rng.randint(lo_hi[0], lo_hi[1])


def generate(rng, bg_key, idx):
    """One recruit, fully rolled (all hidden depth present; reveal gates view)."""
    bg = BACKGROUNDS[bg_key]
    female = rng.random() < 0.12      # 女侠 are genre-core (DESIGN §4.2)
    given = "".join(rng.sample(FEMALE_GIVEN if female else GIVEN,
                               rng.randint(1, 2)))
    name = rng.choice(SURNAMES) + given
    nicks = [n for n in NICKNAME[bg_key]
             if female or n not in FEMALE_NICKS]
    nick = rng.choice(nicks)

    stats = {a: _roll(rng, bg[a]) for a in ATTRS}

    # 0–2 hidden traits, drawn from the background's bias + a little wild
    pool = list(bg["traits"]) + [t for t in TRAITS if rng.random() < 0.15]
    n_traits = rng.choices([0, 1, 2], weights=[25, 50, 25])[0]
    traits = rng.sample(pool, min(n_traits, len(pool))) if pool else []

    # 3 talent stars (60/30/10 for 1/2/3) on distinct attributes — inert until
    # leveling, but the discovery arc is real
    starred = rng.sample(ATTRS, 3)
    talents = {a: rng.choices([1, 2, 3], weights=[60, 30, 10])[0] for a in starred}

    fee = _roll(rng, bg["fee"])
    wage = bg["wage"]
    for t in traits:                  # traits adjust stats + wage at birth
        if t == "shenli":
            pass                      # applied to the weapon at deploy
        elif t == "tiefei":
            stats["breath"] += 12
        elif t == "hanyong":
            stats["resolve"] += 8
        elif t == "danqie":
            stats["resolve"] -= 8
        elif t == "bozu":
            stats["init"] -= 8
        elif t == "lannuo":
            stats["init"] -= 4
        elif t == "jianzhuang":
            stats["hp"] += 6
        elif t == "jieao":
            stats["resolve"] -= 4
            stats["skill"] += 4
        elif t == "jiujiu":
            wage += 1
        elif t == "tanlan":
            wage += 2

    return dict(
        rid=f"{bg_key}_{idx}", name=name, nick=nick, female=female,
        bg=bg_key, bg_name=bg["name"], blurb=bg["blurb"],
        weapon=bg["weapon"], wpn2=bg.get("wpn2"), shield=bg["shield"],
        stats=stats, traits=traits, talents=talents,
        fee=fee, wage=wage, reveal=0)     # reveal: 0 look / 1 gossip / 2 exam


def pool_for(world, settlement):
    """The named candidates a settlement is offering this epoch — deterministic,
    biased by the place (military spots draw harder men, villages softer)."""
    epoch = world.day // REFRESH_DAYS
    rng = _pool_rng(world.rng.seed, settlement["id"], epoch)
    kind = settlement["kind"]
    if kind == "city":
        weights = {"tianong": 2, "tuihuo": 2, "liehu": 2,
                   "huanseng": 1, "tangzishou": 2, "youxia": 1}
    elif kind == "town":
        weights = {"tianong": 3, "tuihuo": 2, "liehu": 2, "tangzishou": 1}
    else:  # village
        weights = {"tianong": 4, "tuihuo": 1, "liehu": 2}
    keys = list(weights)
    out = []
    for i in range(POOL_SIZE):
        bg = rng.choices(keys, weights=[weights[k] for k in keys])[0]
        out.append(generate(rng, bg, i))
    return out


# ---- the graduated reveal (F6): what the player may see, by tier ----
def look(rec):
    """Free: background, fee, wage, and ONE rough hint."""
    bg = BACKGROUNDS[rec["bg"]]
    top = max(rec["stats"], key=lambda a: rec["stats"][a])
    hint = f"看着{'壮实' if top in ('hp', 'breath') else '机警' if top == 'init' else '有把子力气'}"
    return dict(name=rec["name"], nick=rec["nick"], bg_name=rec["bg_name"],
                blurb=rec["blurb"], fee=rec["fee"], wage=rec["wage"], hint=hint,
                weapon=rec["weapon"])


def gossip_cost(rec):
    return max(5, rec["fee"] // 10)


def exam_cost(rec):
    return max(15, rec["fee"] // 4)


def reveal_traits(rec):
    rec["reveal"] = max(rec["reveal"], 1)
    return [TRAITS[t]["name"] for t in rec["traits"]] or ["看不出什么特异"]


def reveal_talents(rec):
    """Exam: the COUNT of stars and ONE attribute's stars — never the full map."""
    rec["reveal"] = max(rec["reveal"], 2)
    total = sum(rec["talents"].values())
    shown = max(rec["talents"], key=lambda a: rec["talents"][a])
    return dict(total_stars=total,
                shown=f"{ATTR_NAME[shown]} {'★' * rec['talents'][shown]}")


def sheet(rec):
    """The character sheet, masked to the revealed tier."""
    s = look(rec)
    if rec["reveal"] >= 1:
        s["traits"] = [TRAITS[t]["name"] for t in rec["traits"]]
    if rec["reveal"] >= 2:
        s["talents"] = reveal_talents(rec)
    s["stats"] = dict(rec["stats"])
    return s


def as_template(rec):
    """A hired character as a battle unit template (data.ROSTER shape), ready
    for deployment. 天生神力 marks the weapon for its +3 at unit build."""
    bg = BACKGROUNDS[rec["bg"]]
    s = rec["stats"]
    return dict(
        id=rec["rid"], name=f"{rec['nick']}{rec['name']}", glyph=bg["glyph"],
        side="player", hp_max=s["hp"], skill=s["skill"], dfn=s["dfn"],
        shield=bg["shield"], resolve=s["resolve"], init_base=s["init"],
        breath_base=s["breath"], armor=bg["armor"], helmet=bg["helmet"],
        wpn=rec["weapon"], wpn2=rec.get("wpn2"),
        recruit_traits=list(rec["traits"]))     # deploy stage reads these
