# Pointy-top axial hex math — 1:1 port of sim/hexmath.py (orientation and
# parity locked, DESIGN.md §7.1 M0). Hexes are Vector2i(q, r).
class_name HexMath

const DIRS: Array[Vector2i] = [
	Vector2i(1, 0), Vector2i(1, -1), Vector2i(0, -1),
	Vector2i(-1, 0), Vector2i(-1, 1), Vector2i(0, 1),
]


static func hex_dist(a: Vector2i, b: Vector2i) -> int:
	var dq := a.x - b.x
	var dr := a.y - b.y
	return (absi(dq) + absi(dr) + absi(dq + dr)) >> 1  # sum is always even


static func neighbors(q: int, r: int) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for d in DIRS:
		out.append(Vector2i(q + d.x, r + d.y))
	return out


static func js_round(x: float) -> int:
	# JS Math.round: half away from zero for positives. Every fraction the
	# rules round goes through this — replay parity depends on it.
	return int(floor(x + 0.5))
