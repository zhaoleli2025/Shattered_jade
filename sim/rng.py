"""Named, seeded RNG streams (DESIGN.md §7): sim code never touches a global RNG.

Streams are independent: consuming "ai" rolls never perturbs "combat" rolls,
so cosmetic/decision randomness can't shift gameplay sequences.
"""
import random


class Streams:
    NAMES = ("combat", "ai", "loot", "worldgen")

    def __init__(self, seed):
        self.seed = seed
        self._streams = {n: random.Random(f"{seed}:{n}") for n in self.NAMES}

    def rint(self, a, b, stream="combat"):
        return self._streams[stream].randint(a, b)

    def d100(self, stream="combat"):
        return self.rint(1, 100, stream)
