"""碎玉 in the terminal — the campaign loop and battles, playable over SSH.

    python3 -m sim.play [world] [seed]        campaign (default: hebei, seed 0)
    python3 -m sim.play battle <scenario> [seed]   one battle, straight in

You command the bureau's units; the AI plays the enemy. Same engine, same
rules, same dice as the web prototype — this is the playtest harness.
"""
import sys

from .ai import ai_turn
from .commands import Stance, Strike, Swap, resolve, targets_of
from .engine import run_battle
from .hexmath import hex_dist
from .overworld import (camp, load_world, raze, travel, dijkstra as wdijkstra,
                        render as wrender)
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


def play_battle(scen_id, seed=0):
    s = load_scenario(scen_id, seed)
    say(f"\n════ {scen_id} · seed {seed} ════")
    r = run_battle(s, {"player": human_turn, "enemy": ai_turn})
    say("\n" + render(s))
    say(f"\n══ 战毕：{'镖局胜' if r['winner'] == 'player' else '敌胜' if r['winner'] == 'enemy' else '平'} · "
        f"{r['rounds']}回合 · 阵亡 {len(r['dead'])} · 溃走 {len(r['escaped'])} ══")
    return r["winner"]


# ---------------- campaign: the realm in the terminal ----------------
WORLD_HELP = """\
  go 地名/id   前往（如: go 定州 / go dingzhou）   go C R  前往 列C 行R
  camp         扎营一日          assault  攻打脚下贼寨
  map          重看舆图          who      已发现的队伍
  q            收兵退出          ?        帮助"""


def world_status(w):
    say("")
    say(wrender(w))
    s = w.at_settlement()
    say(f"\n—— 第{w.day}日 · 粮草{w.provisions} · "
        f"{(s['name'] if s else '野外')} ——")


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
    winner = play_battle(scen, seed=w.day)
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
            for p in w.parties:
                if p.pid in w.spotted and p.alive:
                    say(f"  {p.name}（{p.kind}）在 {p.pos}")
        elif op == "camp":
            enc = camp(w)
            if enc:
                fight_encounter(w, "encounter", enc.pid)
        elif op == "assault":
            s = w.at_settlement()
            if s and s["kind"] == "stronghold" and s["id"] not in w.destroyed:
                winner = play_battle(s.get("scenario", "gongzhai"), seed=w.day)
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
