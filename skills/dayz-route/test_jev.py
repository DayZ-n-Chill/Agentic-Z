"""Tests for jev.py with a mocked urlopen. Never calls the real TypeSafe API."""
import importlib.util
import io
import json
import socket
import urllib.error
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("dayz_route_jev_under_test", Path(__file__).resolve().parent / "jev.py")
jev = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(jev)

TARGETS = {
    "dayz-stop-test": {"kind": "skill", "description": "Stop a test session"},
    "dayz-ui-specialist": {"kind": "agent", "description": "UI work"},
}
KEY = {"TYPESAFE_API_KEY": "test-key"}


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _answer(choice, confidence):
    body = {"model": "jev-latest", "answers": {"route": {"type": "choice", "choice": choice,
            "confidence": confidence, "probabilities": {choice: confidence}}}, "usage": {}}
    return _Resp(json.dumps(body).encode())


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def install(result):
        def fake_urlopen(req, timeout):
            seen.append((req, timeout))
            if isinstance(result, Exception):
                raise result
            return result
        monkeypatch.setattr(jev.urllib.request, "urlopen", fake_urlopen)
        return seen
    return install


def test_no_key_skips_without_http(calls):
    seen = calls(AssertionError("should not be called"))
    assert jev.route("x", TARGETS, {}) == (None, "jev: skipped (TYPESAFE_API_KEY not set)")
    assert seen == []


def test_request_matches_api_contract(calls):
    seen = calls(_answer("dayz-ui-specialist", 0.9))
    decision, _ = jev.route("restyle the HUD", TARGETS, KEY)
    assert decision == {"route": "dayz-ui-specialist", "kind": "agent", "confidence": 0.9, "source": "jev"}
    req, timeout = seen[0]
    assert req.full_url == "https://api.typesafe.ai/v1/systemone"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer test-key"
    assert timeout == jev.TIMEOUT_S
    body = json.loads(req.data)
    assert body["model"] == "jev-latest"
    assert body["state"] == {"request": "restyle the HUD"}
    q = body["questions"]["route"]
    assert q["type"] == "choice"
    assert set(q["criteria"]) == set(TARGETS) | {"other"}


def test_other_means_no_decision(calls):
    calls(_answer("other", 0.8))
    decision, note = jev.route("x", TARGETS, KEY)
    assert decision is None and "no single handler" in note


def test_unknown_choice_is_rejected(calls):
    calls(_answer("rm-rf", 0.99))
    assert jev.route("x", TARGETS, KEY)[0] is None


@pytest.mark.parametrize("error", [
    urllib.error.HTTPError("u", 401, "Unauthorized", {}, None),
    urllib.error.URLError("no network"),
    socket.timeout("timed out"),
])
def test_http_errors_fall_through(calls, error):
    calls(error)
    decision, note = jev.route("x", TARGETS, KEY)
    assert decision is None and note.startswith("jev: failed")


def test_malformed_body_falls_through(calls):
    calls(_Resp(b"{not json"))
    assert jev.route("x", TARGETS, KEY)[0] is None
