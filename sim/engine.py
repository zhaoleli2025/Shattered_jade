"""Turn engine: initiative rounds, upkeep, fleeing, battle loop.

run_battle() is the headless entry point: controllers issue commands per unit
turn; the engine owns upkeep, rout movement, and termination."""
from .hexmath import neighbors
from .pathfind import dijkstra, path_to
from .commands import EndTurn, exec_move, resolve
from .rules import check_end, kill

# Harness extension: the prototype has no round cap or draw concept; the cap
# exists so headless batches always terminate. Real battles peak well below it
# (observed max 27 over 10k fuzzed seeds).
MAX_ROUNDS = 100


def initiative(u):
    return u.init_base - (u.breath_max - u.breath)


def upkeep(state, u):
    """Start-of-turn bookkeeping. Returns False if the unit's turn is skipped."""
    u.shieldwall = False
    u.spearwall = False
    u.breath = min(u.breath_max, u.breath + 15)
    u.ap = 9
    if u.bleed > 0:
        u.bleed -= 1
        u.hp = max(0, u.hp - 5)
        state.emit("bleed", unit=u.uid)
        if u.hp <= 0:
            kill(state, u, None)
            return False
    if u.morale == "Fleeing":
        u.fled_rounds += 1
        adj_enemy = any(
            (e := state.unit_at(*nk)) and e.side != u.side
            for nk in neighbors(u.q, u.r))
        if not adj_enemy and state.rng.d100() <= u.resolve + 10 * u.fled_rounds:
            u.morale = "Wavering"
            state.emit("rally", unit=u.uid)
        else:
            flee_move(state, u)
            return False
    return True


def flee_move(state, u):
    edge_col = state.cols - 1 if u.side == "enemy" else 0
    costs, _brc, prev = dijkstra(state, u, u.ap, u.breath)
    best, best_score = None, 1 << 30
    for k in costs:  # insertion order — first-best wins ties (JS parity)
        t = state.tiles[k]
        score = abs(edge_col - (t.q + (t.r >> 1)))
        if score < best_score:
            best_score, best = score, k
    if best and best != u.pos():
        exec_move(state, u, path_to(prev, best), costs[best])
    if u.alive and state.col_of(u) == edge_col:
        u.alive = False
        u.escaped = True
        state.emit("escape", unit=u.uid)
        check_end(state)


def run_battle(state, controllers, max_rounds=MAX_ROUNDS):
    """controllers: {"player": fn, "enemy": fn}; fn(state, unit) issues commands
    via commands.resolve and returns when the unit's turn is done."""
    while not state.over and state.round < max_rounds:
        state.round += 1
        queue = sorted(state.alive_units(), key=initiative, reverse=True)
        for u in queue:
            if state.over:
                break
            if not u.alive:
                continue
            if not upkeep(state, u):
                continue
            controllers[u.side](state, u)
    if not state.over:
        state.over = True
        state.winner = "draw"
        state.emit("battle_end", winner="draw")
    return summarize(state)


def summarize(state):
    return dict(
        winner=state.winner,
        rounds=state.round,
        survivors={s: [u.uid for u in state.alive_units(s)] for s in ("player", "enemy")},
        dead=[u.uid for u in state.units if not u.alive and not u.escaped],
        escaped=[u.uid for u in state.units if u.escaped],
        events=len(state.events),
    )
