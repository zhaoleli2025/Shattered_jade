"""碎玉 in the terminal — the campaign loop and battles, playable over SSH.

    python3 -m sim.play [world] [seed]        campaign (default: hebei, seed 0)
    python3 -m sim.play battle <scenario> [seed]   one battle, straight in

You command the bureau's units; the AI plays the enemy. Same engine, same
rules, same dice as the web prototype — this is the playtest harness.
"""
import sys

try:
    import readline  # noqa: F401 — arrow keys, history, line editing in input()
except ImportError:
    pass

from .ai import ai_turn
from .commands import Stance, Strike, Swap, resolve, targets_of
from .engine import run_battle
from .hexmath import hex_dist
from .overworld import (atone, battle_wear, camp, dismiss, exam, fail_contract,
                        gossip, hire, jobs, load_world, market_buy, plunder,
                        raze, recruits_here, repair_bill, smith_repair,
                        smith_upgrade, take_job, travel, waylay,
                        dijkstra as wdijkstra, render as wrender)
from . import recruit as rc
from . import progress as pg
from .overworld import award_battle_xp, battle_levels
from .pathfind import dijkstra
from .rules import hit_breakdown
from .state import load_scenario
from .textview import format_event, render
from . import commands as C


def say(*a):
    print(*a)


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        raise SystemExit("\n[输入结束，收兵。]")


# ---------------- battle: the human controller ----------------
BATTLE_HELP = """\
  a N      攻击第 N 个敌人        s N    特技攻击 (横扫: 直接 s)
  m N      向第 N 个敌人推进      m C R  移动到 列C 行R
  w        立枪阵/枪林            d      举盾
  x        换械                   auto   本回合交给 AI
  e        结束该单位行动         log    最近战报
  q        弃战退出               ?      帮助"""


def foes_of(state, u):
    side = "enemy" if u.side == "player" else "player"
    return sorted(state.alive_units(side), key=lambda x: x.uid)


def battle_status(state, u):
    say("")
    say(render(state))
    say(f"\n—— 第{state.round}回合 · {u.name}（{u.glyph}*）"
        f" 血{u.hp}/{u.hp_max} 甲{u.armor_b}/{u.armor_h}"
        f" 行动{u.ap} 气{u.breath} {u.wpn['label']}"
        f"{' 枪阵' if u.spearwall else ''}{' 举盾' if u.shieldwall else ''}")
    reach = {t.uid for t in targets_of(state, u)}
    for i, f in enumerate(foes_of(state, u), 1):
        chance = hit_breakdown(state, u, f)[1] if f.uid in reach else None
        say(f"  [{i}] {f.glyph} {f.name}  血{f.hp}/{f.hp_max} 甲{f.armor_b}/{f.armor_h}"
            f" {f.morale}" + (f"  命中{chance}%" if chance is not None else "  (不在攻程)"))


def pick_foe(state, u, tok):
    foes = foes_of(state, u)
    try:
        return foes[int(tok) - 1]
    except (ValueError, IndexError):
        return None


def move_toward(state, u, target):
    costs, _brc, prev = dijkstra(state, u, u.ap, u.breath)
    best, score = None, (1 << 30, 1 << 30)
    for k, c in costs.items():
        s = (hex_dist(k, target), c)
        if s < score:
            score, best = s, k
    if not best or best == u.pos():
        say("  无路可进。")
        return
    resolve(state, u, C.Move(best))


def human_turn(state, u):
    n0 = len(state.events)
    while u.alive and not state.over and u.morale != "Fleeing":
        battle_status(state, u)
        for e in state.events[n0:]:
            say("  · " + format_event(e))
        n0 = len(state.events)
        toks = ask("指令> ").split()
        if not toks:
            continue
        op = toks[0].lower()
        if op == "e":
            return
        if op == "q":
            raise SystemExit("[弃战。]")
        if op == "?":
            say(BATTLE_HELP)
        elif op == "auto":
            ai_turn(state, u)
            for e in state.events[n0:]:
                say("  · " + format_event(e))
            return
        elif op == "log":
            for e in state.events[-8:]:
                say("  · " + format_event(e))
        elif op == "a" and len(toks) > 1:
            f = pick_foe(state, u, toks[1])
            if not f or not resolve(state, u, Strike(f.uid)):
                say("  打不着（攻程/行动力/气力？）")
        elif op == "s":
            sp = u.wpn.get("special")
            if sp and sp["type"] == "sweep":
                ok = resolve(state, u, Strike("", special=True))
            else:
                f = pick_foe(state, u, toks[1]) if len(toks) > 1 else None
                ok = f and resolve(state, u, Strike(f.uid, special=True))
            if not ok:
                say("  特技施展不得。")
        elif op == "m" and len(toks) == 2:
            f = pick_foe(state, u, toks[1])
            if f:
                move_toward(state, u, f.pos())
        elif op == "m" and len(toks) == 3:
            col, r = int(toks[1]), int(toks[2])
            if not resolve(state, u, C.Move((col - (r >> 1), r))):
                say("  去不了那里。")
        elif op == "w":
            if not resolve(state, u, Stance("spearwall")):
                say("  立不起枪阵。")
        elif op == "d":
            if not resolve(state, u, Stance("shieldwall")):
                say("  举不起盾。")
        elif op == "x":
            if not resolve(state, u, Swap()):
                say("  没有副械或行动力不足。")
        else:
            say("  ? 输入 ? 看指令")


def play_battle(scen_id, seed=0, gear=None, world=None):
    levels = battle_levels(world) if world is not None else None
    s = load_scenario(scen_id, seed, gear=gear, levels=levels)
    say(f"\n════ {scen_id} · seed {seed} ════")
    r = run_battle(s, {"player": human_turn, "enemy": ai_turn})
    say("\n" + render(s))
    say(f"\n══ 战毕：{'镖局胜' if r['winner'] == 'player' else '敌胜' if r['winner'] == 'enemy' else '平'} · "
        f"{r['rounds']}回合 · 阵亡 {len(r['dead'])} · 溃走 {len(r['escaped'])} ══")
    if world is not None:
        battle_wear(world, s)              # the dents ride home
        leveled = award_battle_xp(world, r["winner"] == "player")
        for cid, lv in leveled.items():
            say(f"  ⤴ {cid} 升至 {lv} 级！")
    return r["winner"]


# ---------------- campaign: the realm in the terminal ----------------
WORLD_HELP = """\
  go 地名/id   前往（如: go 定州 / go dingzhou）   go C R  前往 列C 行R
  camp     扎营一日       assault   攻打脚下贼寨
  buy      市集买粮(补满)  jobs      看镖单
  roster   看队伍名册      enlist    看招募榜（候选）
  look N   看相（候选第 N 个）  gossip N  茶馆打探特性  exam N  医馆考较天赋
  hire N   招募候选第 N 个     fire N    遣散第 N 名雇员
  take N   接第 N 单      smith 人 部位   铁匠铺升品 (如: smith wang wpn_q)
  mend 人   修缮甲械（大城/州镇铁铺；如: mend wang）
  map      重看舆图       who       已发现的队伍
  raid N   劫掠身边的商队/巡骑（who 列表第 N 个）
  atone    在大城衙门交赎罪银，洗清恶名
  q        收兵退出       ?         帮助"""


def world_status(w):
    say("")
    say(wrender(w))
    s = w.at_settlement()
    fan = f"（{s['fanzhen']}）" if s and s.get("fanzhen") else ""
    job = f" · 镖单:{w.contract['name']}" if w.contract else ""
    job += f" · 恶名{w.infamy}" if w.infamy else ""
    say(f"\n—— 第{w.day}日 · 银{w.gold}两 · 粮草{w.provisions}/{w.capacity()} · "
        f"{w.headcount()}人(日耗粮{w.daily_food()}·饷{w.daily_wage()}两) · "
        f"{(s['name'] + fan if s else '野外')}{job} ——")


def find_settlement(w, tok):
    for s in w.settlements.values():
        if tok in (s["id"], s["name"]):
            if s.get("hidden") and s["id"] not in w.spotted:
                return None
            return s
    return None


def retreat(w):
    costs, _ = wdijkstra(w, w.party)
    best, bc = None, 1 << 30
    for s in w.settlements.values():
        if s["kind"] not in ("city", "town", "village") or s["id"] in w.destroyed:
            continue
        c = costs.get(s["at"], 1 << 30)
        if c < bc:
            bc, best = c, s
    if best:
        w.party = best["at"]
        w.provisions = max(w.provisions, 4)
        say(f"  残部退守{best['name']}。")


def fight_encounter(w, pend_kind, target_id):
    e = next(ev for ev in reversed(w.events) if ev["type"] == "encounter")
    scen = e["scenario"]
    say(f"\n⚔ {e['name']}拦路！地势：{e['terrain']}"
        + (f"（{w.sites[e['site']]['name']}）" if e.get("site") else "")
        + f" → 【{scen}】")
    if ask("开战 (y) / 脱离 (n) > ").lower() not in ("y", "yes", "战", ""):
        say("  且退一射之地。")
        return
    winner = play_battle(scen, seed=w.day, gear=w.gear, world=w)
    if winner == "player":
        if pend_kind == "assault":
            raze(w, target_id)
            say(f"  {w.settlements[target_id]['name']}已荡平！")
        else:
            p = next((p for p in w.parties if p.pid == target_id), None)
            if p:
                p.alive = False
                say(f"  {p.name}就此覆灭，道路为之一清。")
    else:
        say("  败了。")
        fail_contract(w)
        retreat(w)


def play_campaign(world_id="hebei", seed=0):
    w = load_world(world_id, seed)
    say(f"════ {w.spec['name']} · {w.spec['era']} · seed {seed} ════")
    say("镖局总号驻" + w.at_settlement()["name"] + "。输入 ? 看指令。")
    while True:
        world_status(w)
        toks = ask("舆图> ").split()
        if not toks:
            continue
        op = toks[0].lower()
        if op == "q":
            say("[收兵。]")
            return
        if op == "?":
            say(WORLD_HELP)
        elif op == "map":
            continue
        elif op == "who":
            for i, p in enumerate((p for p in w.parties
                                   if p.pid in w.spotted and p.alive), 1):
                say(f"  [{i}] {p.name}（{p.kind}）在 {p.pos}")
        elif op == "raid" and len(toks) > 1:
            seen = [p for p in w.parties if p.pid in w.spotted and p.alive]
            try:
                target = seen[int(toks[1]) - 1]
            except (ValueError, IndexError):
                target = None
            p = waylay(w, target.pid) if target else None
            if not p:
                say("  够不着，或那不是能劫的队伍。")
            else:
                e = w.events[-1]
                say(f"  伏于道旁，劫{p.name}——【{e['scenario']}】")
                winner = play_battle(e["scenario"], seed=w.day, gear=w.gear, world=w)
                if winner == "player":
                    pay = plunder(w, p.pid)
                    say(f"  得手！掠得{pay}两。官府闻之必怒。")
                else:
                    say("  劫道失手，败走。")
                    fail_contract(w)
                    retreat(w)
        elif op == "camp":
            enc = camp(w)
            if enc:
                fight_encounter(w, "encounter", enc.pid)
        elif op == "atone":
            cost = atone(w)
            say(f"  赎罪银{cost}两已纳，恶名洗清。" if cost
                else "  衙门只在大城，或无恶名/银两不济。")
        elif op == "buy":
            n = market_buy(w)
            say(f"  市集购粮{n}。" if n else "  此地无市，或银两不济。")
        elif op == "roster":
            for cid in w.roster:
                sh = pg.sheet(w.progress[cid])
                say(f"  {cid} Lv{sh['level']}（距下级{sh['to_next']}经验）"
                    f" {' '.join(sh['rows'])}")
            for i, m in enumerate(w.members, 1):
                pr = w.progress.get(m.get("rid"))
                lvl = f"Lv{pr['level']}" if pr else ""
                say(f"  [{i}] {m.get('nick','')}·{m['name']}（{m.get('bg_name','')} {lvl} 饷{m['wage']}）")
            if not w.members:
                say("  尚无雇员。")
        elif op == "enlist":
            pool = recruits_here(w)
            for i, r in enumerate(pool, 1):
                tag = "·".join(rc.TRAITS[t]["name"] for t in r["traits"]) if r["reveal"] >= 1 else "？"
                say(f"  [{i}] {r['nick']}·{r['name']}（{r['bg_name']}）"
                    f"雇{r['fee']} 饷{r['wage']} 特性：{tag}")
            if not pool:
                say("  此地无招募榜。")
        elif op in ("look", "gossip", "exam", "hire") and len(toks) > 1:
            pool = recruits_here(w)
            try:
                r = pool[int(toks[1]) - 1]
            except (ValueError, IndexError):
                say("  无此候选。"); continue
            if op == "look":
                s = rc.sheet(r)
                say(f"  {r['nick']}·{r['name']}（{r['bg_name']}）—— {r['blurb']}")
                say("  " + " ".join(f"{rc.ATTR_NAME[a]}{v}" for a, v in s['stats'].items()))
                say(f"  {s['hint']}；兵器 {r['weapon']}")
                if r["reveal"] >= 1:
                    say("  特性：" + ("、".join(rc.TRAITS[t]["name"] for t in r["traits"]) or "无"))
                if r["reveal"] >= 2:
                    tl = rc.reveal_talents(r)
                    say(f"  天赋：共{tl['total_stars']}星，{tl['shown']}")
            elif op == "gossip":
                tr = gossip(w, r["rid"])
                say("  茶馆道：" + "、".join(tr) if tr else "  打探不得（已知或银两不足）。")
            elif op == "exam":
                tl = exam(w, r["rid"])
                say(f"  考较：共{tl['total_stars']}星，{tl['shown']}" if tl
                    else "  考较不得（已知或银两不足）。")
            elif op == "hire":
                say(f"  {r['nick']}·{r['name']}入伙！" if hire(w, r["rid"])
                    else "  招不得（银两不足）。")
        elif op == "fire" and len(toks) > 1:
            try:
                ok = dismiss(w, int(toks[1]) - 1)
            except ValueError:
                ok = False
            say("  已遣散。" if ok else "  无此雇员。")
        elif op == "jobs":
            board = jobs(w)
            for i, j in enumerate(board, 1):
                say(f"  [{i}] {j['name']}  {j['pay']}两")
            if not board:
                say("  此地无镖单。")
        elif op == "take" and len(toks) > 1:
            board = jobs(w)
            try:
                job = board[int(toks[1]) - 1]
            except (ValueError, IndexError):
                job = None
            if job and take_job(w, job):
                say(f"  接下镖单：{job['name']}（{job['pay']}两）")
            else:
                say("  接不了（已有在身镖单？）")
        elif op == "mend" and len(toks) == 2:
            bill = repair_bill(w, toks[1])
            paid = smith_repair(w, toks[1])
            say(f"  修缮完毕，费银{paid}两。" if paid
                else (f"  无需修缮。" if bill == 0
                      else f"  需{bill}两（银两不足，或不在城镇）。"))
        elif op == "smith" and len(toks) == 3:
            g = smith_upgrade(w, toks[1], toks[2])
            say(f"  打造完成：{toks[1]} {toks[2]} → {g}" if g
                else "  铁匠铺只在大城，或银两/品阶不济。")
        elif op == "assault":
            s = w.at_settlement()
            if s and s["kind"] == "stronghold" and s["id"] not in w.destroyed:
                winner = play_battle(s.get("scenario", "gongzhai"), seed=w.day,
                                     gear=w.gear, world=w)
                if winner == "player":
                    raze(w, s["id"])
                    say(f"  {s['name']}已荡平！")
                else:
                    say("  攻寨失利。")
                    retreat(w)
            else:
                say("  脚下并无可攻之寨。")
        elif op == "go" and len(toks) == 3 and toks[1].lstrip("-").isdigit():
            col, r = int(toks[1]), int(toks[2])
            d = travel(w, (col - (r >> 1), r))
            _after_travel(w, d)
        elif op == "go" and len(toks) > 1:
            s = find_settlement(w, toks[1])
            if not s:
                say("  不识此地（贼巢须先探得）。")
                continue
            d = travel(w, s["id"])
            _after_travel(w, d)
        else:
            say("  ? 输入 ? 看指令")


def _after_travel(w, days):
    if days is None:
        say("  无路可达。")
        return
    last = w.events[-1]
    if last["type"] == "travel" and last.get("intercepted"):
        fight_encounter(w, "encounter", last["intercepted"])
    else:
        say(f"  行程{days}日。")


def main(argv):
    if argv and argv[0] == "battle":
        scen = argv[1] if len(argv) > 1 else "jiebiao"
        seed = int(argv[2]) if len(argv) > 2 else 0
        play_battle(scen, seed)
    else:
        world_id = argv[0] if argv else "hebei"
        seed = int(argv[1]) if len(argv) > 1 else 0
        play_campaign(world_id, seed)


if __name__ == "__main__":
    main(sys.argv[1:])
