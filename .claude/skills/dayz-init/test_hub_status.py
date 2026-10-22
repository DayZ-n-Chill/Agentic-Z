"""Tests for dayz-init/hub_status.py."""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_status  # noqa: E402
from state import write_state  # noqa: E402


def test_status_reads_active_mod_pbo_and_servers(tmp_path, monkeypatch):
    monkeypatch.setattr(hub_status, "_diag_running", lambda: False)
    monkeypatch.setattr(hub_status, "SEARCH_INDEX", tmp_path / "no-index")
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    project = tmp_path / "clone"
    write_state(project, {"last_intent": {"mod_name": "MyMod"}})
    for name in ("chernarus", "livonia", "!ClientDiagLogs"):
        (project / ".server" / name).mkdir(parents=True)
    for name in ("chernarus", "livonia"):
        (project / ".server" / name / "serverDZ.cfg").write_text("", encoding="utf-8")
    pbo = tmp_path / "Mods" / "@MyMod" / "Addons" / "MyMod.pbo"
    pbo.parent.mkdir(parents=True)
    pbo.write_bytes(b"")
    old = time.time() - 600
    os.utime(pbo, (old, old))

    s = hub_status.gather_status(project, mods_root=tmp_path / "Mods")
    assert s.mod == "MyMod"
    assert s.servers == ["chernarus", "livonia"]
    assert 9 <= s.pbo_age_minutes <= 11
    text = hub_status.render_status(s)
    assert "/dayz-init: MyMod" in text
    assert "Search:  not set up" in text


def test_voyage_key_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nVOYAGE_API_KEY=\n")
    assert not hub_status._voyage_key_set(env)
    env.write_text("VOYAGE_API_KEY=pa-abc\n")
    assert hub_status._voyage_key_set(env)


def test_search_status_wording():
    base = dict(project=Path("."), mod="M", pbo_age_minutes=None, servers=[], diag_running=False)
    ready = hub_status.render_status(hub_status.Status(**base, voyage_key=True, search_index=True))
    no_key = hub_status.render_status(hub_status.Status(**base, voyage_key=False, search_index=True))
    assert "Search:  ready" in ready
    assert "VOYAGE_API_KEY missing" in no_key
    assert "PBO:     not built yet" in ready


def test_behavior_copies_and_folders_without_a_config_are_not_servers(tmp_path):
    server_dir = tmp_path / ".server"
    for name in ("chernarus", "chernarus-behavior", "half-made", "!Health"):
        (server_dir / name).mkdir(parents=True)
    for name in ("chernarus", "chernarus-behavior", "!Health"):
        (server_dir / name / "serverDZ.cfg").write_text("", encoding="utf-8")
    assert hub_status._test_servers(server_dir) == ["chernarus"]


def test_non_vanilla_required_addons_are_listed(tmp_path, monkeypatch):
    monkeypatch.setattr(hub_status, "_diag_running", lambda: False)
    project = tmp_path / "clone"
    write_state(project, {"last_intent": {"mod_name": "MyMod"}})
    cfg = project / "workspace" / "MyMod" / "config.cpp"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        'class CfgPatches { class MyMod { requiredAddons[] = {"DZ_Data", "JM_CF_Scripts"}; }; };\n'
        '// requiredAddons[] = {"Commented_Out"};\n',
        encoding="utf-8",
    )
    s = hub_status.gather_status(project, mods_root=tmp_path / "Mods")
    assert s.needs == ["JM_CF_Scripts"]
    assert "Needs:   JM_CF_Scripts" in hub_status.render_status(s)


def test_prebuilt_bundle_has_no_needs_line(tmp_path, monkeypatch):
    # dispatch.py launch and plan.py do not ask a bundle for --deps, so the hub must not either.
    monkeypatch.setattr(hub_status, "_diag_running", lambda: False)
    project = tmp_path / "clone"
    write_state(project, {"last_intent": {"mod_name": "MyBundle"}})
    mod = project / "workspace" / "MyBundle"
    (mod / "Addons").mkdir(parents=True)
    (mod / "Addons" / "part.pbo").write_bytes(b"")
    (mod / "config.cpp").write_text(
        'class CfgPatches { class MyBundle { requiredAddons[] = {"JM_CF_Scripts"}; }; };\n', encoding="utf-8"
    )
    s = hub_status.gather_status(project, mods_root=tmp_path / "Mods")
    assert s.needs == []
    assert "Needs:" not in hub_status.render_status(s)
