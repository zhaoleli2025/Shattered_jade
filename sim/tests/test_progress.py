"""BB attribute growth: baseline, upper limit, star-accelerated per-level gains."""
import random

from sim import progress as pg
from sim import recruit as rc


def base():
    return dict(hp=48, skill=52, dfn=6, resolve=40, init=100, breath=88)


def test_baseline_cap_and_growth():
    prog = pg.new_progress(base(), {"skill": 2})
    assert prog["level"] == 1 and prog["stats"]["skill"] == 52
    assert pg.cap_of(prog, "skill") == 52 + 28        # base + room = upper limit
    assert pg.cap_of(prog, "hp") == 48 + 55
    rng = random.Random(0)
    g = pg.level_up(prog, rng)
    assert prog["level"] == 2 and len(g) <= 3
    for a, gain in g.items():
        lo, hi = pg.GROW[a]["per"]
        assert lo <= gain <= hi + pg.stars(prog, a)    # within the star-lifted band
        assert prog["stats"][a] <= pg.cap_of(prog, a)  # never past the limit


def test_stars_accelerate_and_reveal():
    """A 3-star attribute grows far faster than a 0-star one, and the star shows."""
    rng = random.Random(3)
    star = pg.new_progress(base(), {"skill": 3})       # 武艺 prodigy
    plain = pg.new_progress(base(), {"hp": 1})          # 武艺 untalented
    for _ in range(10):                                 # a full career to L11
        pg.level_up(star, rng)
        pg.level_up(plain, rng)
    assert star["stats"]["skill"] - 52 > plain["stats"]["skill"] - 52 + 8
    assert "skill" in star["revealed"]                  # leveling unmasked the star
    assert star["stats"]["skill"] <= pg.cap_of(star, "skill")


def test_caps_are_hard():
    prog = pg.new_progress(base(), {"dfn": 3})          # tiny room (16) + big stars
    rng = random.Random(1)
    for _ in range(10):
        pg.level_up(prog, rng)
    assert prog["stats"]["dfn"] == pg.cap_of(prog, "dfn")   # pinned at the ceiling


def test_xp_curve_drives_levels():
    prog = pg.new_progress(base(), {})
    rng = random.Random(2)
    assert pg.level_for_xp(0) == 1 and pg.level_for_xp(15000) == 11
    ups = pg.award_xp(prog, 1050, rng)                  # straight to level 4
    assert prog["level"] == 4 and len(ups) == 3
    assert pg.xp_to_next(prog) == pg.LEVEL_XP[5] - 1050


def test_a_recruit_levels():
    r = rc.generate(random.Random("hero"), "tianong", 0)   # a humble 佃农
    prog = pg.new_progress(r["stats"], r["talents"])
    rng = random.Random(9)
    pg.award_xp(prog, 15000, rng)                       # a whole storied career
    assert prog["level"] == 11
    assert all(prog["stats"][a] >= r["stats"][a] for a in rc.ATTRS)  # only grew
