"""BB-style recruitment: named characters, hidden depth, the graduated reveal."""
from sim import recruit as rc
from sim.overworld import (exam, gossip, hire, load_world, recruits_here)


def test_generate_is_a_whole_person():
    import random
    rng = random.Random("x")
    r = rc.generate(rng, "youxia", 0)
    assert r["bg_name"] == "游侠" and r["nick"] and r["name"]
    assert set(r["stats"]) == set(rc.ATTRS)
    assert 60 <= r["stats"]["skill"] <= 72        # youxia skill range (+trait room)
    assert len(r["talents"]) == 3 and all(1 <= v <= 3 for v in r["talents"].values())
    assert r["fee"] >= 200 and r["reveal"] == 0   # nothing revealed yet


def test_traits_actually_bend_the_stats():
    import random
    # find a recruit with 铁肺 and confirm the +12 breath landed
    for seed in range(200):
        r = rc.generate(random.Random(seed), "liehu", 0)
        if "tiefei" in r["traits"]:
            assert r["stats"]["breath"] >= 88 + 12 - 6   # base hi 94, +12, minus other
            break
    else:
        raise AssertionError("no 铁肺 in 200 rolls — bias broken")


def test_pool_is_deterministic_and_place_biased():
    w1, w2 = load_world("hebei"), load_world("hebei")
    p1 = [r["rid"] for r in recruits_here(w1)]
    p2 = [r["rid"] for r in recruits_here(w2)]
    assert p1 == p2 and len(p1) == rc.POOL_SIZE   # same seed → same candidates
    # a village musters softer men than a city
    w = load_world("hebei")
    w.party = w.settlements["wangdu"]["at"]
    village = {r["bg"] for r in recruits_here(w)}
    assert village <= {"tianong", "tuihuo", "liehu"}   # no 游侠/趟子手 in a hamlet


def test_graduated_reveal_then_hire():
    w = load_world("hebei")
    w.gold = 999
    pool = recruits_here(w)
    rec = pool[0]
    assert rc.sheet(rec).get("traits") is None        # a free look hides traits
    traits = gossip(w, rec["rid"])
    assert traits is not None and rec["reveal"] >= 1   # 茶馆 reveals them
    tal = exam(w, rec["rid"])
    assert "total_stars" in tal and rec["reveal"] == 2  # 医馆: count + one attr
    assert hire(w, rec["rid"]) is True
    assert any(m["rid"] == rec["rid"] for m in w.members)
    assert rec not in recruits_here(w)                 # gone from the board


def test_hire_costs_fee_and_grows_upkeep():
    w = load_world("hebei")
    w.gold = 999
    rec = recruits_here(w)[0]
    g0, hc0, wage0 = w.gold, w.headcount(), w.daily_wage()
    hire(w, rec["rid"])
    assert w.gold == g0 - rec["fee"]
    assert w.headcount() == hc0 + 1
    assert w.daily_wage() == wage0 + rec["wage"]       # his wage joins the drain
