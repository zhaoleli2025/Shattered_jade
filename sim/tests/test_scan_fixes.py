"""Pins for the 2026-06-11 folder-scan fixes (surround friendly fire,
scenario-id validation, batch weapon attribution, standalone freshness)."""
import json
import os

import pytest

import sim.state as state
from sim.rules import hit_breakdown
from sim.run_batch import weapon_at_event
from sim.state import load_scenario


def surround_part(parts):
    return next((v for label, v in parts if label == "surround"), None)


def test_surround_never_applies_to_friendly_fire():
    """DESIGN §3.6: 围攻 never helps you hit your own man (大斧 sweep case)."""
    s = load_scenario("jiebiao")
    wang, liu, shi = s.by_id("wang"), s.by_id("liu"), s.by_id("shi")
    s.by_id("duyan").q, s.by_id("duyan").r = 9, 0  # clear the neighborhood
    liu.q, liu.r = 5, 5      # defender
    wang.q, wang.r = 4, 5    # attacker, adjacent
    shi.q, shi.r = 6, 4      # second friendly melee adjacent to the defender
    parts, _ = hit_breakdown(s, wang, liu)
    assert surround_part(parts) is None


def test_surround_still_applies_to_enemies():
    s = load_scenario("jiebiao")
    wang, shi, duyan = s.by_id("wang"), s.by_id("shi"), s.by_id("duyan")
    s.by_id("liu").q, s.by_id("liu").r = 0, 0
    duyan.q, duyan.r = 5, 5  # defender (enemy)
    wang.q, wang.r = 4, 5
    shi.q, shi.r = 6, 4      # two player melee adjacent → +5
    parts, _ = hit_breakdown(s, wang, duyan)
    assert surround_part(parts) == 5


def test_load_scenario_rejects_unknown_unit_ids(tmp_path, monkeypatch):
    spec = {"map": {"cols": 3, "rows": 3},
            "units": [{"id": "nobody", "spawn": [0, 0]}]}
    (tmp_path / "bogus.json").write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.setattr(state, "SCENARIO_DIR", str(tmp_path))
    with pytest.raises(ValueError, match=r"bogus.*nobody"):
        load_scenario("bogus")


def test_weapon_at_event_swap_parity():
    """run_batch attributes each swing to the weapon held at event time by
    walking swap parity back from the final state."""
    s = load_scenario("jiebiao")
    yan = s.by_id("yan")  # bow main, dagger sidearm
    liu = s.by_id("liu")  # no sidearm
    assert weapon_at_event(yan, 0) is yan.wpn
    assert weapon_at_event(yan, 1) is yan.wpn2   # one swap still ahead → other weapon
    assert weapon_at_event(yan, 2) is yan.wpn    # even parity → current weapon
    assert weapon_at_event(liu, 5) is liu.wpn    # sidearm-less: parity is moot


def test_standalone_html_matches_builder_output():
    """The standalone is a build artifact; hand edits / stale rebuilds fail here.
    Regenerate with: python3 tools/build_standalone.py"""
    from tools.build_standalone import OUT, build
    with open(OUT, encoding="utf-8") as f:
        on_disk = f.read()
    assert on_disk == build(), "standalone stale — run python3 tools/build_standalone.py"


def test_weapon_dicts_are_private_per_unit():
    """make_unit deep-copies weapons so nested 'special' dicts are never shared."""
    a = load_scenario("jiebiao").by_id("wang")
    b = load_scenario("jiebiao").by_id("wang")
    assert a.wpn is not b.wpn
    assert a.wpn["special"] is not b.wpn["special"]
    from sim.data import WEAPONS
    assert a.wpn["special"] is not WEAPONS["changqiang"]["special"]
