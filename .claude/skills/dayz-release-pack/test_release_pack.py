"""Tests for release_pack.py against the fixture mod. No P: drive, no DayZ."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "MyVest"
_SPEC = importlib.util.spec_from_file_location("dayz_release_pack_under_test", HERE / "release_pack.py")
rp = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rp)


@pytest.fixture
def mod(tmp_path):
    dest = tmp_path / "MyVest"
    shutil.copytree(FIXTURE, dest)
    return dest


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
                    "-c", "tag.gpgsign=false", *args], cwd=cwd, check=True, capture_output=True)


def commit(repo, path, subject):
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(old + "\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", subject)


def pack(mod, tmp_path, **kw):
    out = tmp_path / "out"
    report = rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-21", **kw)
    return report, {p.name: p.read_text(encoding="utf-8") for p in out.iterdir()}


def test_writes_the_four_files(mod, tmp_path):
    report, files = pack(mod, tmp_path, deps=["@CF"])
    assert sorted(files) == ["changelog.md", "classnames.md", "server-install.md", "workshop-description.txt"]
    assert report["load_order"] == ["@CF", "@MyVest"]


def test_classnames_follow_scope_through_parents(mod, tmp_path):
    report, files = pack(mod, tmp_path)
    # MyVest_Base is scope 0, MyVest_Hidden inherits it, MyVest_Pouch uses the word "public".
    assert report["spawnable"] == ["MyVest_Black", "MyVest_Green", "MyVest_Pouch"]
    assert report["unresolved"] == ["MyVest_Patch"]
    table = files["classnames.md"]
    assert "| `MyVest_Black` | CfgVehicles | MyVest_Base | Tactical Vest (Black) |" in table
    assert "MyVest_Hidden" not in table and "`MyVest_Base`" not in table
    assert "- `MyVest_Patch` (parent `Armband_ColorBase`)" in table
    [warning] = [w for w in report["warnings"] if w.startswith("scope-unknown")]
    assert "set an explicit scope in config.cpp" in warning and "by hand" not in warning
    assert "by hand" not in table


def test_workshop_text_uses_mod_cpp_and_bbcode(mod, tmp_path):
    _, files = pack(mod, tmp_path, deps=["CF"])
    text = files["workshop-description.txt"]
    assert text.startswith("[h1]Tactical Vest[/h1]\n\nAdds a tactical vest in two colors.")
    assert "[*]Tactical Vest (Black) (MyVest_Black)" in text
    assert "[*]MyVest_Green\n" in text  # a stringtable key is not a name a player reads
    assert "[*]@CF" in text


def test_server_kit_line_is_a_link_to_fill_in(mod, tmp_path):
    report, files = pack(mod, tmp_path)
    assert "[url=SERVER_KIT_LINK]server kit[/url]" in files["workshop-description.txt"]
    assert "The server kit has" not in files["workshop-description.txt"]
    assert any(w.startswith("server-kit-link") for w in report["warnings"])


def test_summary_falls_back_to_readme_then_placeholder(mod, tmp_path):
    (mod / "mod.cpp").unlink()
    (mod / "README.md").write_text("# MyVest\n\n![badge](x.png)\n\nA vest for\nsurvivors.\n\n## Install\n", encoding="utf-8")
    _, files = pack(mod, tmp_path)
    assert "[h1]MyVest[/h1]\n\nA vest for survivors." in files["workshop-description.txt"]
    (mod / "README.md").unlink()
    report, files = pack(mod, tmp_path)
    assert rp.SUMMARY_PLACEHOLDER in files["workshop-description.txt"]
    assert any(w.startswith("summary-missing") for w in report["warnings"])


def test_unmapped_dependency_is_a_warning(mod, tmp_path):
    report, files = pack(mod, tmp_path)
    assert any(w.startswith("deps-unmapped") and "JM_CF_Scripts" in w for w in report["warnings"])
    assert "JM_CF_Scripts" in files["server-install.md"]
    assert "DZ_Data" not in files["workshop-description.txt"]


def test_install_notes_name_the_key_and_load_order(mod, tmp_path):
    _, files = pack(mod, tmp_path, deps=["CF"])
    notes = files["server-install.md"]
    assert "Copy `MyVest.bikey` from `@MyVest\\Keys\\`" in notes
    assert "`-mod=@CF;@MyVest`" in notes
    assert "MyVest_ce" in notes


def test_missing_key_and_private_key_warn(mod, tmp_path):
    (mod / "Keys" / "MyVest.bikey").unlink()
    (mod / "Keys" / "MyVest.biprivatekey").write_bytes(b"secret")
    report, files = pack(mod, tmp_path)
    assert any(w.startswith("no-bikey") for w in report["warnings"])
    assert any(w.startswith("private-key-in-mod") for w in report["warnings"])
    assert "biprivatekey" not in "".join(files.values())


def test_changelog_from_git_groups_conventional_commits(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat: add the black vest")
    git(mod, "tag", "v1.0.0")
    commit(mod, mod / "config.cpp", "feat(config): add the green vest")
    commit(mod, mod / "mod.cpp", "fix: green vest texture path")
    commit(mod, mod / "notes.txt", "update notes")
    commit(mod, mod / "notes.txt", "chore(release): 1.1.0")
    report, files = pack(mod, tmp_path, version="1.1.0")
    entry = files["changelog.md"]
    assert entry.startswith("## 1.1.0 (2026-10-21)")
    assert "### Added\n\n- Add the green vest" in entry
    assert "### Fixed\n\n- Green vest texture path" in entry
    assert "### Changed\n\n- Update notes" in entry
    assert "black vest" not in entry  # before the latest tag
    assert "1.1.0" not in entry.split("\n", 1)[1]  # the release commit is left out
    assert report["changes"] == {"since": "v1.0.0", "from": "tag", "commits": 3}
    assert "changelog starts after v1.0.0, the latest tag" in rp.render_text(report)
    assert "[h2]Changes in 1.1.0[/h2]" in files["workshop-description.txt"]

    # HEAD~2..HEAD holds "update notes" and the skipped release commit.
    report, files = pack(mod, tmp_path, version="1.1.0", since="HEAD~2")
    assert report["changes"]["commits"] == 1


def test_own_repo_without_tags_warns_full_history(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat: add the black vest")
    commit(mod, mod / "config.cpp", "feat: add the green vest")
    report, files = pack(mod, tmp_path)
    assert report["changes"] == {"since": None, "from": None, "commits": 2}
    [warning] = [w for w in report["warnings"] if w.startswith("changelog-full-history")]
    assert "git tag v<version>" in warning and "--since" in warning


def test_mod_inside_a_bigger_repo_ignores_its_tags(tmp_path):
    repo = tmp_path / "clone"
    mod = repo / "workspace" / "MyVest"
    repo.mkdir()
    git(repo, "init", "-q")
    commit(repo, repo / "README.md", "chore: template")
    git(repo, "tag", "v9.0.0")
    shutil.copytree(FIXTURE, mod)
    commit(repo, mod / "config.cpp", "feat: add the vest")
    commit(repo, repo / "README.md", "docs: template only")
    report, files = pack(mod, tmp_path)
    assert report["changes"] == {"since": None, "from": None, "commits": 1}
    assert "- Add the vest" in files["changelog.md"]
    assert any(w.startswith("changelog-full-history") and "--since <ref>" in w for w in report["warnings"])


def test_mod_inside_a_bigger_repo_starts_after_its_last_release_commit(tmp_path):
    repo = tmp_path / "clone"
    mod = repo / "workspace" / "MyVest"
    repo.mkdir()
    git(repo, "init", "-q")
    shutil.copytree(FIXTURE, mod)
    commit(repo, mod / "config.cpp", "feat: add the black vest")
    commit(repo, mod / "notes.txt", "chore(release): 1.0.0")
    commit(repo, repo / "README.md", "chore(release): template 2.0.0")  # not in the mod folder
    commit(repo, mod / "config.cpp", "feat: add the green vest")
    report, files = pack(mod, tmp_path, version="1.1.0")
    release = subprocess.run(["git", "log", "-1", "--format=%h", "--grep=1.0.0"], cwd=repo,
                             capture_output=True, text=True, check=True).stdout.strip()
    assert report["changes"] == {"since": release, "from": "release-commit", "commits": 1}
    assert "- Add the green vest" in files["changelog.md"] and "black vest" not in files["changelog.md"]
    assert not any(w.startswith("changelog-") for w in report["warnings"])
    assert f"changelog starts after {release}" in rp.render_text(report)


def test_no_commits_since_the_start_warns(tmp_path):
    repo = tmp_path / "clone"
    mod = repo / "workspace" / "MyVest"
    repo.mkdir()
    git(repo, "init", "-q")
    shutil.copytree(FIXTURE, mod)
    commit(repo, mod / "notes.txt", "chore(release): 1.0.0")
    commit(repo, repo / "README.md", "docs: template only")
    report, files = pack(mod, tmp_path, version="1.0.1")
    assert report["changes"]["commits"] == 0
    assert any(w.startswith("changelog-empty: no commits touched the mod folder since ") for w in report["warnings"])
    assert "No commits touched the mod folder since" in files["changelog.md"]


def test_no_git_says_so(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "_git", lambda *a: None)
    report, files = pack(mod, tmp_path)
    assert "No git history" in files["changelog.md"]
    assert any(w.startswith("no-git") for w in report["warnings"])


def test_bad_since_ref_is_an_error(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat: one")
    with pytest.raises(rp.ReleaseError, match="not a commit"):
        pack(mod, tmp_path, since="nope")


def test_broken_config_is_an_error(mod, tmp_path):
    (mod / "config.cpp").write_text("class CfgPatches {\n", encoding="utf-8")
    with pytest.raises(rp.ReleaseError, match="dayz-lint"):
        pack(mod, tmp_path)


def test_cli_json_and_errors(mod, tmp_path):
    out = tmp_path / "cli"
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py"), "--mod-dir", str(mod), "--out", str(out),
                        "--deps", "CF", "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["load_order"] == ["@CF", "@MyVest"]
    assert (out / "workshop-description.txt").is_file()
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py"), "--mod-dir", str(tmp_path / "missing")],
                       capture_output=True, text=True)
    assert r.returncode == 2 and r.stdout.startswith("[FAIL]")
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py")], capture_output=True, text=True)
    assert r.returncode == 2
