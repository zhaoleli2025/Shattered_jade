"""Minimal ASCII view of a battle state — the sim core never imports this."""


def render(state):
    rows = []
    for r in range(state.rows):
        cells = []
        for col in range(state.cols):
            q = col - (r >> 1)
            u = state.unit_at(q, r)
            t = state.tiles[(q, r)]
            if u:
                mark = u.glyph
                mark += "!" if u.morale != "Steady" else ("*" if u.side == "player" else " ")
            else:
                mark = {"forest": "竹 ", "hill": "丘 ", "road": "= ",
                        "cart": "镖 ", "wall": "栅 ", "grass": ". "}[t.terrain]
                if t.elev == 2 and t.terrain == "hill":
                    mark = "岭 "
                if t.elev == 3:
                    mark = "峰 "
            cells.append(mark)
        rows.append((" " if r % 2 else "") + " ".join(cells))
    return "\n".join(rows)


def format_event(e):
    t = e["type"]
    if t == "hit":
        return (f"R{e['round']} {e['atk']}→{e['dfn']} {e['chance']}% d100={e['roll']} HIT"
                f"{' HEAD' if e['head'] else ''} dmg={e['dmg']} armor-{e['armor_dmg']} hp-{e['hp_dmg']}"
                f"{' [' + e['tag'] + ']' if e.get('tag') else ''}")
    if t == "miss":
        return f"R{e['round']} {e['atk']}→{e['dfn']} {e['chance']}% d100={e['roll']} MISS"
    return f"R{e['round']} {t} " + " ".join(f"{k}={v}" for k, v in e.items()
                                            if k not in ("type", "round"))
