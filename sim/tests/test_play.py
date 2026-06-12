"""The terminal game: scripted-input smoke of both modes."""
import builtins
import itertools

from sim import play


def test_terminal_battle_completes(monkeypatch):
    feeds = itertools.chain(["?", "log"], itertools.repeat("auto"))
    monkeypatch.setattr(builtins, "input", lambda *_: next(feeds))
    assert play.play_battle("duijue", seed=5) in ("player", "enemy", "draw")


def test_terminal_campaign_loop(monkeypatch, capsys):
    feeds = iter(["?", "camp", "go dingzhou", "who", "q"])
    monkeypatch.setattr(builtins, "input", lambda *_: next(feeds))
    play.play_campaign("hebei", seed=4)          # returns cleanly on q
    out = capsys.readouterr().out
    assert "定州" in out and "收兵" in out
