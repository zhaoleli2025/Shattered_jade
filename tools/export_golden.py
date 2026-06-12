"""Export golden parity vectors from the Python sim for the Godot port (M1).

The GDScript port must reproduce the Python sim bit-for-bit; these JSON vectors
are the contract. Deterministic (fixed seed) — the files change only when the
rules change. Rerun after any change to a ported module, then run the Godot
headless suite:

    python3 tools/export_golden.py
    /data/zhaoleli/opt/godot/godot --headless --path godot --script tests/run_tests.gd
"""
import json
import os
import random
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.hexmath import hex_dist, js_round  # noqa: E402

OUT_DIR = os.path.join(ROOT, "godot", "tests", "golden")


def hexmath_vectors():
    rng = random.Random(0)
    dist = [dict(a=[rng.randint(-12, 24), rng.randint(-4, 12)],
                 b=[rng.randint(-12, 24), rng.randint(-4, 12)])
            for _ in range(200)]
    for c in dist:
        c["d"] = hex_dist(tuple(c["a"]), tuple(c["b"]))
    xs = ([n + 0.5 for n in range(-10, 11)]            # the half-edges JS and Python disagree on
          + [n / 4 for n in range(-40, 41)]
          + [rng.uniform(-150, 150) for _ in range(120)]
          + [126.49999999999999, 6.5, -6.5, 0.49999999999999994])  # float-dust pins
    # xb = IEEE-754 bits (little-endian hex): Godot's JSON parser drops the 17th
    # significant digit, so decimal text is NOT a bit-exact transport for doubles.
    return dict(hex_dist=dist,
                js_round=[dict(x=x, xb=struct.pack("<d", x).hex(), r=js_round(x))
                          for x in xs])


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "hexmath.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hexmath_vectors(), f, separators=(",", ":"))
    print(f"wrote {path}")
