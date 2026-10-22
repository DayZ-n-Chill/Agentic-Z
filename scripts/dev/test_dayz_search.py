"""Tests for the terminal search CLI (scripts/dayz/dayz-search.py).

The search itself is stubbed, so these run without an index or a Voyage key.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "dayz" / "dayz-search.py"
_spec = importlib.util.spec_from_file_location("dayz_search_cli", SCRIPT)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

HIT = {
    "path": r"P:\scripts\4_world\entities\itembase.c", "line_start": 10, "line_end": 12,
    "distance": 0.25, "parent_context": "class ItemBase", "snippet": "void OnStoreSave()\n{\n}",
    "is_stale": False,
}


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def fake(query, top_k, file_type, max_distance):
        seen.append((query, top_k, file_type, max_distance))
        return [HIT]

    monkeypatch.setattr(cli, "search_dayz_source_impl", fake)
    return seen


def test_formatted_output(calls, capsys):
    assert cli.main(["-k", "3", "store", "save"]) == 0
    out = capsys.readouterr().out
    assert calls == [("store save", 3, None, None)]
    assert r"[1] P:\scripts\4_world\entities\itembase.c:10-12  distance=0.250" in out
    assert "    class ItemBase" in out
    assert "    | void OnStoreSave()" in out


def test_json_output(calls, capsys):
    assert cli.main(["-j", "-t", "cpp", "vest"]) == 0
    assert json.loads(capsys.readouterr().out) == [HIT]
    assert calls[0][2] == "cpp"


def test_snippet_is_cut(calls, capsys):
    cli.main(["-s", "5", "q"])
    assert "    | void ..." in capsys.readouterr().out


def test_no_hits(monkeypatch, capsys):
    monkeypatch.setattr(cli, "search_dayz_source_impl", lambda *a, **k: [])
    assert cli.main(["q"]) == 0
    assert "(no hits)" in capsys.readouterr().out


@pytest.mark.parametrize("ft", ["cpp", "hpp", "h", "c", "layout"])
def test_every_server_file_type_is_accepted(calls, ft):
    assert cli.main(["-t", ft, "q"]) == 0


def test_bad_file_type_is_an_argparse_error(calls, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["-t", "config.cpp", "q"])
    assert e.value.code == 2
    assert calls == []


@pytest.mark.parametrize("exc", [RuntimeError("no index, run /dayz-search-index"), ValueError("bad"),
                                 FileNotFoundError("manifest.json")])
def test_search_errors_print_one_line_and_exit_2(monkeypatch, capsys, exc):
    def boom(*_a, **_k):
        raise exc

    monkeypatch.setattr(cli, "search_dayz_source_impl", boom)
    assert cli.main(["q"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "Traceback" not in err


def test_missing_package_names_the_requirements_file(monkeypatch, capsys):
    def boom(*_a, **_k):
        raise ImportError("No module named 'lancedb'")

    monkeypatch.setattr(cli, "search_dayz_source_impl", boom)
    assert cli.main(["q"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: No module named 'lancedb'") and "requirements.txt" in err


def test_voyage_error_prints_one_line_and_exits_2(monkeypatch, capsys):
    class AuthenticationError(Exception):
        """Stands in for voyageai.error.AuthenticationError."""

    def boom(*_a, **_k):
        raise AuthenticationError("invalid key")

    monkeypatch.setattr(cli, "search_dayz_source_impl", boom)
    assert cli.main(["q"]) == 2
    err = capsys.readouterr().err
    assert err == "error: AuthenticationError: invalid key\n"


def test_empty_query(calls, capsys):
    assert cli.main(["   "]) == 2
    assert "empty query" in capsys.readouterr().err
