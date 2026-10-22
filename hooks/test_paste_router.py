"""Tests for the UserPromptSubmit paste-in hook (paste_router.py): one per paste type,
plus the promises that it is fast and never blocks a prompt."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "paste_router.py"
_spec = importlib.util.spec_from_file_location("paste_router_under_test", SCRIPT)
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def _run(prompt, project: Path, raw: str | bytes | None = None) -> subprocess.CompletedProcess:
    payload = raw if raw is not None else json.dumps({
        "session_id": "s", "cwd": str(project), "hook_event_name": "UserPromptSubmit", "prompt": prompt,
    })
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    if isinstance(payload, bytes):  # raw bytes, as Claude Code pipes them, whatever the locale codec
        r = subprocess.run([sys.executable, str(SCRIPT)], input=payload, capture_output=True, env=env, timeout=30)
        return subprocess.CompletedProcess(r.args, r.returncode, r.stdout.decode("utf-8"), r.stderr.decode("utf-8", "replace"))
    return subprocess.run([sys.executable, str(SCRIPT)], input=payload, capture_output=True, text=True,
                          env=env, timeout=30)


def _context(r: subprocess.CompletedProcess) -> str | None:
    assert r.returncode == 0
    if not r.stdout.strip():
        return None
    out = json.loads(r.stdout)
    assert "decision" not in out  # context only, never a block
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "UserPromptSubmit"
    return spec["additionalContext"]


# --- normal prompts -----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "build MyVest",
    "make the AK spawn less often in types.xml",
    "my server crashes on startup, can you look?",
    "convert vest_co.png to .paa",
    "",
])
def test_normal_prompts_get_no_context(tmp_path, prompt):
    assert _context(_run(prompt, tmp_path)) is None


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", '{"prompt": 5}'])
def test_bad_input_never_blocks(tmp_path, raw):
    r = _run(None, tmp_path, raw=raw)
    assert r.returncode == 0 and r.stdout == ""


def test_hook_is_fast_for_a_big_paste(tmp_path):
    log = "\n".join(f"10:{i % 60:02d}:00 Some ordinary log line {i}" for i in range(20000))
    log += "\n10:59:59 SCRIPT    (E): NULL pointer to instance\n"
    start = time.perf_counter()
    context = _context(_run(log, tmp_path))
    assert time.perf_counter() - start < 5
    assert "known null-pointer" in context


def test_a_bug_in_a_paste_handler_never_blocks(tmp_path, monkeypatch, capsys):
    def boom(*a):
        raise RuntimeError("bug")

    monkeypatch.setattr(pr, "log_context", boom)
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps({"prompt": "SCRIPT (E): x"})))
    assert pr.main() == 0
    assert capsys.readouterr().out == ""


# --- crash log or RPT -----------------------------------------------------------------

RPT = (
    "My car crashes the server, here is the RPT:\n"
    "10:01:02.123 SCRIPT    (E): NULL pointer to instance\n"
    "10:01:03.456 SCRIPT    (E): NULL pointer to instance\n"
    "10:01:04 Unhandled exception\n"
)


def test_pasted_log_is_triaged_and_only_new_lines_go_to_the_debugger(tmp_path):
    context = _context(_run(RPT, tmp_path))
    assert "found 1 known and 1 new" in context
    assert "known null-pointer" in context and "seen 2x" in context
    assert "fix:" in context
    assert "new (line 4" in context and "Unhandled exception" in context
    assert "Dispatch dayz-mod-debugger with only the new lines" in context


def test_all_known_log_needs_no_debugger(tmp_path):
    context = _context(_run("10:01:02 SCRIPT    (E): NULL pointer to instance", tmp_path))
    assert "dayz-mod-debugger is not needed" in context


def test_non_ascii_paste_is_read_as_utf8(tmp_path):
    prompt = "10:01:02 SCRIPT    (E): NULL pointer to instance ”ok”"
    raw = json.dumps({"session_id": "s", "cwd": str(tmp_path), "hook_event_name": "UserPromptSubmit",
                      "prompt": prompt}, ensure_ascii=False).encode("utf-8")
    context = _context(_run(None, tmp_path, raw=raw))
    assert "”ok" in context
    assert "â€" not in context


def test_learned_errors_of_the_project_count_as_known(tmp_path):
    learned = tmp_path / ".claude" / "local-memory" / "dayz-gate-known-errors.json"
    learned.parent.mkdir(parents=True)
    triage = pr._load("t", pr.TRIAGE)
    entry = {"id": "my-crash", "fingerprint": triage.fingerprint("Unhandled exception"),
             "meaning": "m", "fix": "f", "owner_agent": "dayz-script-specialist"}
    learned.write_text(json.dumps([entry]), encoding="utf-8")
    context = _context(_run("10:01:04 Unhandled exception", tmp_path))
    assert "known my-crash" in context


# --- types.xml chunk -------------------------------------------------------------------

GOOD = ('<type name="MyMod_Vest"><nominal>5</nominal><lifetime>7200</lifetime><restock>0</restock><min>2</min>'
        '<quantmin>-1</quantmin><quantmax>-1</quantmax><cost>100</cost><flags count_in_map="1"/></type>')


def test_types_chunk_is_checked_and_sent_to_merge(tmp_path):
    context = _context(_run(f"add these to my server:\n{GOOD}\n{GOOD.replace('MyMod_Vest', 'MyMod_Hat')}", tmp_path))
    assert "2 types.xml <type> entries" in context
    assert "--merge <chunk> --dry-run" in context
    assert "must be fixed" not in context


def test_types_chunk_problems_are_listed(tmp_path):
    bad = GOOD.replace("<min>2", "<min>9")
    context = _context(_run(bad, tmp_path))
    assert "MyMod_Vest: min (9) is greater than nominal (5)" in context


def test_types_chunk_with_trailing_prose_holding_a_bracket(tmp_path):
    context = _context(_run(f"{GOOD}\nthen merge -> chernarus, like `type a > b`", tmp_path))
    assert "1 types.xml <type> entry" in context
    assert "do not parse as XML" not in context


def test_unparseable_types_chunk_says_so(tmp_path):
    context = _context(_run('<type name="X"><nominal>5</type>', tmp_path))
    assert "do not parse as XML" in context


@pytest.mark.parametrize("prompt", ['in my types.xml <type name="X"> has nominal 0, why?',
                                    'what does <type name = "AK101"> mean in types.xml?'])
def test_type_named_in_prose_is_not_a_paste(tmp_path, prompt):
    assert _context(_run(prompt, tmp_path)) is None


@pytest.mark.parametrize("chunk", ['<type name="X"/>', '<type name="X">\n  <nominal>5</nominal>'])
def test_self_closing_or_cut_off_entries_are_still_checked(tmp_path, chunk):
    assert "<type> entr" in _context(_run(chunk, tmp_path))


# --- links ---------------------------------------------------------------------------

def test_figma_link_starts_the_pipeline(tmp_path):
    context = _context(_run("https://www.figma.com/design/abc123/Trader?node-id=10-42", tmp_path))
    assert "figma-node-normalizer, then figma-to-dayz-layout, then dayz-layout-validator" in context


def test_github_link_goes_to_import(tmp_path):
    context = _context(_run("can you work on https://github.com/Owner/MyVest?", tmp_path))
    assert "/dayz-import-mod --source https://github.com/Owner/MyVest" in context


def test_github_tree_link_keeps_the_branch(tmp_path):
    context = _context(_run("import github.com/Owner/MyVest/tree/dev please", tmp_path))
    assert "--source github.com/Owner/MyVest/tree/dev" in context


def test_github_tree_link_keeps_a_branch_with_a_slash(tmp_path):
    context = _context(_run("import https://github.com/Owner/MyVest/tree/feature/x please", tmp_path))
    assert "--source https://github.com/Owner/MyVest/tree/feature/x " in context


def test_hyphenated_repo_gets_a_valid_name(tmp_path):
    context = _context(_run("import https://github.com/salutesh/DayZ-Expansion please", tmp_path))
    assert "--source https://github.com/salutesh/DayZ-Expansion --name DayZExpansion " in context


def test_valid_repo_gets_no_name():
    assert pr.name_arg("https://github.com/Owner/MyVest") == ""
    assert pr.name_arg("https://github.com/Owner/Mods/tree/main/MyMod") == ""


def test_hyphenated_subfolder_is_named_after_the_subfolder():
    assert pr.name_arg("https://github.com/Owner/Mods/tree/main/my-vest") == " --name myvest"
    assert pr.name_arg("github.com/Owner/my-mods/tree/main/Vest") == " --name Vest"


def test_mod_name_rule_matches_import_mod():
    new_mod = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "dayz-new-mod" / "new_mod.py"
    assert pr.MOD_NAME_RE.pattern in new_mod.read_text(encoding="utf-8")


@pytest.mark.parametrize("link", ["https://github.com/DayZ-n-Chill/Agentic-Z/pull/86",
                                  "https://github.com/Owner/MyVest/issues/3",
                                  "https://github.com/Owner/MyVest/blob/main/config.cpp",
                                  "https://github.com/Owner/My.Vest/commit/abc123",
                                  "https://github.com/Owner/MyVest/releases",
                                  "https://github.com/Owner/MyVest/wiki/Setup",
                                  "https://github.com/Owner/MyVest/settings",
                                  "https://github.com/orgs/DayZ-n-Chill/repositories",
                                  "https://github.com/settings/profile",
                                  "https://github.com/features/actions",
                                  "https://github.com/trending/python",
                                  "https://github.com/collections/machine-learning",
                                  "https://gist.github.com/Owner/abc123",
                                  "https://github.com/advisories/GHSA-abcd-1234",
                                  "https://github.com/sponsors/Owner",
                                  "https://github.com/marketplace/actions",
                                  "https://github.com/notifications/beta",
                                  "https://github.com/login/oauth",
                                  "https://github.com/organizations/plan"])
def test_github_link_that_is_not_a_repo_adds_no_context(tmp_path, link):
    assert _context(_run(f"review {link}", tmp_path)) is None


def test_plugin_copy_steps_aside_for_the_project_copy(tmp_path, monkeypatch, capsys):
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "paste_router.py").write_text("", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert pr.shadowed_by_project()  # this copy lives outside tmp_path, like a plugin copy
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps({"prompt": "https://github.com/O/R"})))
    assert pr.main() == 0
    assert capsys.readouterr().out == ""


def test_project_copy_does_not_step_aside(monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(SCRIPT.parents[1]))
    assert not pr.shadowed_by_project()


def test_a_bug_in_the_shadow_check_never_blocks(monkeypatch, capsys):
    def boom():
        raise OSError("bad path")

    monkeypatch.setattr(pr, "shadowed_by_project", boom)
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps({"prompt": "SCRIPT (E): x"})))
    assert pr.main() == 0
    assert capsys.readouterr().out == ""


def test_one_failing_detector_keeps_the_others(monkeypatch):
    def boom(*a):
        raise RuntimeError("bug")

    monkeypatch.setattr(pr, "types_context", boom)
    context = pr.build_context(f"[Image #1]\n{RPT}\n<type name=\"X\"></type>", Path("."))
    assert "DayZ log lines" in context and "screenshot" in context


@pytest.mark.parametrize("link", ["https://steamcommunity.com/sharedfiles/filedetails/?id=1559212036",
                                  "steam://url/CommunityFilePage/1559212036"])
def test_workshop_link_is_refused(tmp_path, link):
    context = _context(_run(f"import {link}", tmp_path))
    assert "Do not download, unpack or import it" in context
    assert "binarized" in context and "protected" in context
    assert "/dayz-import-mod" not in context.split("refuses it")[1]  # no import offered after the refusal


# --- screenshots -------------------------------------------------------------------------

@pytest.mark.parametrize("prompt", ["[Image #1] my compass is in the wrong place",
                                    r"here is a screenshot: C:\shots\bug.png"])
def test_screenshot_gets_the_routing_rule(tmp_path, prompt):
    context = _context(_run(prompt, tmp_path))
    for agent in ("dayz-ui-specialist", "dayz-asset-specialist", "dayz-script-specialist"):
        assert agent in context


def test_several_pastes_in_one_prompt_all_get_context(tmp_path):
    context = _context(_run(f"[Image #1]\n{RPT}\n{GOOD}", tmp_path))
    assert "DayZ log lines" in context and "<type> entr" in context and "screenshot" in context


# --- registration ------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("config, root", [("hooks/hooks.json", "${CLAUDE_PLUGIN_ROOT}"),
                                          (".claude/settings.json", "$CLAUDE_PROJECT_DIR")])
def test_hook_is_registered_for_plugin_and_clone(config, root):
    hooks = json.loads((REPO / config).read_text(encoding="utf-8"))["hooks"]["UserPromptSubmit"]
    commands = [h["command"] for entry in hooks for h in entry["hooks"]]
    assert f'python "{root}/hooks/paste_router.py"' in commands
