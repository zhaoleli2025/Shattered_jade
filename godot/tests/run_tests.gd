# Headless parity suite: pins the GDScript sim-core port to golden vectors
# exported from the Python sim (tools/export_golden.py). Exit 0 = parity.
#   /data/zhaoleli/opt/godot/godot --headless --path . --script tests/run_tests.gd
extends SceneTree

const HexMathPort := preload("res://sim_core/hex_math.gd")


func _init() -> void:
	var failures := _test_hexmath()
	if failures == 0:
		print("PARITY OK — GDScript port matches the Python sim")
		quit(0)
	else:
		printerr("%d golden-vector mismatches" % failures)
		quit(1)


func _load_golden(name: String) -> Dictionary:
	var f := FileAccess.open("res://tests/golden/%s.json" % name, FileAccess.READ)
	assert(f != null, "golden file missing — run python3 tools/export_golden.py")
	return JSON.parse_string(f.get_as_text())


func _test_hexmath() -> int:
	var g := _load_golden("hexmath")
	var bad := 0
	for c in g["hex_dist"]:
		var got := HexMathPort.hex_dist(
			Vector2i(int(c["a"][0]), int(c["a"][1])),
			Vector2i(int(c["b"][0]), int(c["b"][1])))
		if got != int(c["d"]):
			bad += 1
			printerr("hex_dist %s→%s: got %d, want %d" % [c["a"], c["b"], got, int(c["d"])])
	for c in g["js_round"]:
		# bit-exact transport: JSON text loses the 17th digit, the hex bits don't
		var x := (c["xb"] as String).hex_decode().decode_double(0)
		var got := HexMathPort.js_round(x)
		if got != int(c["r"]):
			bad += 1
			printerr("js_round(%s): got %d, want %d" % [c["x"], got, int(c["r"])])
	print("hexmath: %d + %d vectors checked" % [g["hex_dist"].size(), g["js_round"].size()])
	return bad
