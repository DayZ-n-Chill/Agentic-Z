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
    return report, {p.name: p.read_text(encoding="utf-8") for p in out.iterdir() if not p.name.startswith(".")}


def test_writes_the_four_files(mod, tmp_path):
    report, files = pack(mod, tmp_path, deps=["@CF"])
    assert sorted(files) == ["changelog.md", "classnames.md", "server-install.md", "workshop-description.txt"]
    assert report["load_order"] == ["@CF", "@MyVest"]
    state = json.loads((tmp_path / "out" / rp.STATE_FILE).read_text(encoding="utf-8"))
    assert sorted(state) == sorted(files) and state["changelog.md"] == rp._hash(files["changelog.md"])


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


def test_wrong_or_partial_deps_still_warn(mod, tmp_path):
    # --deps that does not ship JM_CF_Scripts must not silence the warning.
    report, _ = pack(mod, tmp_path, deps=["SomethingElse"])
    [warning] = [w for w in report["warnings"] if w.startswith("deps-unmapped")]
    assert "JM_CF_Scripts" in warning and "SomethingElse" in warning and "check that every listed addon" in warning
    # Two non-vanilla addons and one dependency mod: still a check to settle.
    cfg = mod / "config.cpp"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace('"JM_CF_Scripts"', '"JM_CF_Scripts", "Other_Addon"'),
                   encoding="utf-8")
    report, _ = pack(mod, tmp_path, deps=["CF"])
    assert any(w.startswith("deps-unmapped") and "Other_Addon" in w and "['CF']" in w for w in report["warnings"])


def test_vanilla_only_mod_has_no_deps_warning(mod, tmp_path):
    cfg = mod / "config.cpp"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace(', "JM_CF_Scripts"', ""), encoding="utf-8")
    for deps in (None, ["CF"]):
        report, _ = pack(mod, tmp_path, deps=deps)
        assert not any(w.startswith("deps-unmapped") for w in report["warnings"])


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


def test_tag_on_head_starts_after_the_tag_before_it(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat: add the black vest")
    git(mod, "tag", "v0.9.0")
    commit(mod, mod / "config.cpp", "feat: add the green vest")
    git(mod, "tag", "v1.0.0")  # tagged before writing the notes
    report, files = pack(mod, tmp_path, version="1.0.0")
    assert report["changes"] == {"since": "v0.9.0", "from": "tag", "commits": 1, "skipped": "v1.0.0"}
    assert "- Add the green vest" in files["changelog.md"] and "black vest" not in files["changelog.md"]
    assert not any(w.startswith("changelog-") for w in report["warnings"])
    assert "changelog starts after v0.9.0, the tag before v1.0.0" in rp.render_text(report)


def test_tag_matching_version_is_skipped_when_not_on_head(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat: add the black vest")
    git(mod, "tag", "v0.9.0")
    commit(mod, mod / "config.cpp", "feat: add the green vest")
    git(mod, "tag", "1.0.0")
    commit(mod, mod / "mod.cpp", "fix: green vest texture path")
    report, files = pack(mod, tmp_path, version="1.0.0")
    assert report["changes"]["since"] == "v0.9.0" and report["changes"]["skipped"] == "1.0.0"
    assert "Add the green vest" in files["changelog.md"] and "Green vest texture path" in files["changelog.md"]


def test_only_tag_on_head_lists_whole_history(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat: add the black vest")
    git(mod, "tag", "v1.0.0")
    report, files = pack(mod, tmp_path, version="1.0.0")
    assert report["changes"] == {"since": None, "from": None, "commits": 1, "skipped": "v1.0.0"}
    assert "- Add the black vest" in files["changelog.md"]
    [warning] = [w for w in report["warnings"] if w.startswith("changelog-")]
    assert warning.startswith("changelog-full-history: v1.0.0 is this release")


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
    monkeypatch.setattr(rp, "_git_installed", lambda: True)
    monkeypatch.setattr(rp, "_git", lambda *a: None)
    report, files = pack(mod, tmp_path)
    assert "No git history" in files["changelog.md"]
    assert any(w.startswith("no-git: the mod folder is not in a git repository") for w in report["warnings"])


def test_git_not_installed_is_told_apart(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "_git_installed", lambda: False)
    report, files = pack(mod, tmp_path)
    assert "git is not installed" in files["changelog.md"]
    [warning] = [w for w in report["warnings"] if w.startswith("no-git")]
    assert "git is not installed or not on PATH" in warning and "not in a git repository" not in warning


def test_bad_since_ref_is_an_error(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat: one")
    with pytest.raises(rp.ReleaseError, match="not a commit"):
        pack(mod, tmp_path, since="nope")


def test_broken_config_is_an_error(mod, tmp_path):
    (mod / "config.cpp").write_text("class CfgPatches {\n", encoding="utf-8")
    with pytest.raises(rp.ReleaseError, match="dayz-lint"):
        pack(mod, tmp_path)


SUBFOLDER_ROOT = """class CfgPatches
{
	class MyVest
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data"};
	};
};
"""

SUBFOLDER_DATA = """class CfgPatches
{
	class MyVest_Data
	{
		units[] = {"MyVest_Black"};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"MyVest", "DZ_Characters_Vests", "JM_CF_Scripts"};
	};
};
class CfgVehicles
{
	class Vest_Base;
	class MyVest_Base: Vest_Base
	{
		scope = 0;
	};
	class MyVest_Black: MyVest_Base
	{
		scope = 2;
		displayName = "Tactical Vest (Black)";
	};
	class MyVest_Stripe: MyVest_Gear
	{
	};
};
"""


def test_items_in_a_subfolder_config_are_read(mod, tmp_path):
    # A root config.cpp with only CfgPatches, and the items in data/config.cpp.
    (mod / "config.cpp").write_text(SUBFOLDER_ROOT, encoding="utf-8")
    (mod / "data").mkdir()
    (mod / "data" / "config.cpp").write_text(SUBFOLDER_DATA, encoding="utf-8")
    # A parent defined in a third file still sets the scope of a child in data/.
    (mod / "gear").mkdir()
    (mod / "gear" / "config.cpp").write_text(
        "class CfgVehicles\n{\n\tclass Clothing;\n\tclass MyVest_Gear: Clothing\n\t{\n\t\tscope = 2;\n\t};\n};\n",
        encoding="utf-8")
    # Built PBO sources, keys and dot folders are not the mod's source config.
    for skipped in ("Addons", "Keys", ".git"):
        (mod / skipped).mkdir(exist_ok=True)
        (mod / skipped / "config.cpp").write_text("class CfgVehicles { class Skipped_Item { scope = 2; }; };\n",
                                                  encoding="utf-8")
    report, files = pack(mod, tmp_path)
    assert report["configs"] == ["config.cpp", "data/config.cpp", "gear/config.cpp"]
    assert report["spawnable"] == ["MyVest_Black", "MyVest_Stripe", "MyVest_Gear"]
    assert "Skipped_Item" not in files["classnames.md"]
    assert "| `MyVest_Black` | CfgVehicles | MyVest_Base | Tactical Vest (Black) | `data/config.cpp` |" in files["classnames.md"]
    facts = rp.mod_facts("MyVest", mod, p_mods=None)
    assert facts["patches"] == ["MyVest", "MyVest_Data"]
    # The mod's own patch class is not a dependency; the sub-folder's other addons are.
    assert facts["required_addons"] == ["DZ_Data", "DZ_Characters_Vests", "JM_CF_Scripts"]
    assert any(w.startswith("deps-unmapped") and "JM_CF_Scripts" in w and "'MyVest'" not in w
               for w in report["warnings"])
    assert "spawnable classes from config.cpp, data/config.cpp, gear/config.cpp" in rp.render_text(report)


def test_class_in_two_configs_is_listed_once_and_warned(mod, tmp_path):
    (mod / "data").mkdir()
    (mod / "data" / "config.cpp").write_text(
        "class CfgVehicles\n{\n\tclass Vest_Base;\n\tclass MyVest_Black: Vest_Base\n\t{\n\t\tscope = 0;\n\t};\n};\n",
        encoding="utf-8")
    report, files = pack(mod, tmp_path)
    assert report["spawnable"].count("MyVest_Black") == 1  # the root definition wins
    assert any(w.startswith("class-duplicate") and "MyVest_Black" in w for w in report["warnings"])


def test_no_config_anywhere_is_an_error(mod, tmp_path):
    (mod / "config.cpp").unlink()
    (mod / "Addons").mkdir()
    (mod / "Addons" / "config.cpp").write_text("class CfgPatches {};\n", encoding="utf-8")
    with pytest.raises(rp.ReleaseError, match="no config.cpp under"):
        pack(mod, tmp_path)


def test_broken_subfolder_config_is_an_error(mod, tmp_path):
    (mod / "data").mkdir()
    (mod / "data" / "config.cpp").write_text("class CfgVehicles {\n", encoding="utf-8")
    with pytest.raises(rp.ReleaseError, match=r"data.config\.cpp.*dayz-lint"):
        pack(mod, tmp_path)


def test_rerun_keeps_an_edited_workshop_description(mod, tmp_path):
    out = tmp_path / "out"
    rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-21", deps=["CF"])
    desc = out / "workshop-description.txt"
    edited = desc.read_text(encoding="utf-8").replace("SERVER_KIT_LINK", "https://example.com/kit.zip")
    desc.write_text(edited, encoding="utf-8")
    report = rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-21", deps=["CF"])
    assert (out / "workshop-description.txt.bak").read_text(encoding="utf-8") == edited
    assert "SERVER_KIT_LINK" in desc.read_text(encoding="utf-8")
    assert any(w.startswith("kept-backup:") and "workshop-description.txt.bak" in w for w in report["warnings"])
    # Unchanged files get no backup, and a second edited rerun never replaces the first backup.
    assert not (out / "classnames.md.bak").exists()
    desc.write_text("second edit\n", encoding="utf-8")
    rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-21", deps=["CF"])
    assert (out / "workshop-description.txt.bak").read_text(encoding="utf-8") == edited
    assert (out / "workshop-description.txt.2.bak").read_text(encoding="utf-8") == "second edit\n"
    report = rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-21", deps=["CF"])
    assert not any(w.startswith("kept-backup:") for w in report["warnings"])


def test_rerun_without_hand_edits_keeps_no_backup(mod, tmp_path):
    # A later day changes the changelog date, a mod change changes the texts: neither is a hand edit.
    out = tmp_path / "out"
    rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-21", deps=["CF"])
    report = rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-22", deps=["CF"])
    (mod / "mod.cpp").write_text((mod / "mod.cpp").read_text(encoding="utf-8").replace(
        "two colors", "three colors"), encoding="utf-8")
    report2 = rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-23", deps=["CF"])
    assert not list(out.glob("*.bak"))
    assert not any(w.startswith("kept-backup") for w in report["warnings"] + report2["warnings"])
    assert (out / "changelog.md").read_text(encoding="utf-8").startswith("## Unreleased (2026-10-23)")
    assert "three colors" in (out / "workshop-description.txt").read_text(encoding="utf-8")
    # A hand edit on a later day is still backed up.
    desc = out / "workshop-description.txt"
    desc.write_text(desc.read_text(encoding="utf-8").replace("SERVER_KIT_LINK", "https://example.com/kit"),
                    encoding="utf-8")
    report = rp.release_pack("MyVest", mod, out, p_mods=None, date="2026-10-24", deps=["CF"])
    assert [p.name for p in out.glob("*.bak")] == ["workshop-description.txt.bak"]
    assert any(w.startswith("kept-backup") for w in report["warnings"])


def test_mod_dir_output_defaults_to_the_repo_output(mod, tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    monkeypatch.setattr(rp, "REPO", repo)
    monkeypatch.chdir(mod)  # running from inside the mod folder must not write into it
    name, mod_dir, out = rp.resolve_mod(None, Path("."), None)
    assert (name, mod_dir) == ("MyVest", mod.resolve())
    assert out == (repo / "output" / "MyVest-release").resolve()
    with pytest.raises(rp.ReleaseError, match="inside the mod folder"):
        rp.resolve_mod(None, mod, mod / "output" / "MyVest-release")
    with pytest.raises(rp.ReleaseError, match="inside the mod folder"):
        rp.resolve_mod(None, mod, mod)


def test_cli_refuses_an_output_folder_inside_the_mod(mod, tmp_path):
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py"), "--mod-dir", str(mod), "--out",
                        str(mod / "release")], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("[FAIL]") and "inside the mod folder" in r.stderr
    assert not (mod / "release").exists()


def test_cli_json_and_errors(mod, tmp_path):
    out = tmp_path / "cli"
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py"), "--mod-dir", str(mod), "--out", str(out),
                        "--deps", "CF", "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["load_order"] == ["@CF", "@MyVest"]
    assert (out / "workshop-description.txt").is_file()
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py"), "--mod-dir", str(tmp_path / "missing")],
                       capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("[FAIL]") and "[FAIL]" not in r.stdout
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py")], capture_output=True, text=True)
    assert r.returncode == 2



def test_bbcode_in_commits_and_names_is_shown_not_parsed(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "fix: list [b]bold[/b] items [/noparse] too")
    (mod / "mod.cpp").write_text('name = "Vest [url=x]y[/url]";\noverview = "Adds [i]a vest[/i].";\n', encoding="utf-8")
    _, files = pack(mod, tmp_path)
    text = files["workshop-description.txt"]
    assert "[*][noparse]List [b]bold[/b] items [/ noparse] too[/noparse]" in text
    assert "[h1][noparse]Vest [url=x]y[/url][/noparse][/h1]" in text
    assert "[noparse]Adds [i]a vest[/i].[/noparse]" in text
    assert text.count("[noparse]") == text.count("[/noparse]")
    assert "- List [b]bold[/b] items [/noparse] too" in files["changelog.md"]  # Markdown needs no escaping


def test_breaking_commits_get_their_own_heading(mod, tmp_path):
    git(mod, "init", "-q")
    commit(mod, mod / "config.cpp", "feat!: rename all classes")
    path = mod / "notes.txt"
    path.write_text("x\n", encoding="utf-8")
    git(mod, "add", "-A")
    git(mod, "commit", "-q", "-m", "refactor: new prefix", "-m", "BREAKING CHANGE: old classnames are gone")
    commit(mod, mod / "config.cpp", "feat: add the green vest")
    _, files = pack(mod, tmp_path)
    entry = files["changelog.md"]
    assert "### Breaking changes\n\n- New prefix\n- Rename all classes\n" in entry
    assert entry.index("### Breaking changes") < entry.index("### Added")
    assert "### Added\n\n- Add the green vest\n" in entry and "Rename all classes" not in entry.split("### Added")[1]
    text = files["workshop-description.txt"]
    assert "[*][b]Breaking:[/b] Rename all classes" in text and "[*][b]Breaking:[/b] New prefix" in text


def test_internal_commits_stay_out_of_the_workshop_text(mod, tmp_path):
    git(mod, "init", "-q")
    for subject in ("docs: explain the vest", "test: add unit tests", "ci: run lint", "build(deps): bump",
                    "style: format", "refactor: split config", "chore: tidy", "fix: vest texture"):
        commit(mod, mod / "notes.txt", subject)
    _, files = pack(mod, tmp_path)
    text = files["workshop-description.txt"]
    assert "[*]Vest texture" in text
    for line in ("Add unit tests", "Explain the vest", "Run lint", "Bump", "Format", "Split config", "Tidy"):
        assert line not in text
        assert f"- {line}\n" in files["changelog.md"].split("### Internal")[1]
    # Only internal work since the start: the Workshop text says so instead of "First release".
    git(mod, "tag", "v1.0.0")
    commit(mod, mod / "notes.txt", "docs: more")
    _, files = pack(mod, tmp_path)
    assert "No player-facing changes since v1.0.0." in files["workshop-description.txt"]
    assert "### Internal\n\n- More" in files["changelog.md"]


def test_cli_deps_swallowing_the_mod_name_is_a_clear_error(mod, tmp_path):
    script = str(HERE / "release_pack.py")
    r = subprocess.run([sys.executable, script, "--deps", "CF", "MyVest"], capture_output=True, text=True)
    assert r.returncode == 2 and "'MyVest' was read as a dependency" in r.stderr and "before --deps" in r.stderr
    # With --mod-dir the name is taken from the folder, so a swallowed name is the mod itself.
    r = subprocess.run([sys.executable, script, "--mod-dir", str(mod), "--out", str(tmp_path / "o"),
                        "--deps", "CF", "MyVest"], capture_output=True, text=True)
    assert r.returncode == 2 and "names the mod itself" in r.stderr
    assert not (tmp_path / "o").exists()


def test_cli_repeated_deps_add_up(mod, tmp_path):
    r = subprocess.run([sys.executable, str(HERE / "release_pack.py"), "--mod-dir", str(mod), "--out",
                        str(tmp_path / "o"), "--deps", "CF", "--deps", "@COT", "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["load_order"] == ["@CF", "@COT", "@MyVest"]


def test_no_bikey_names_an_unmounted_drive(mod, tmp_path):
    (mod / "Keys" / "MyVest.bikey").unlink()
    p_mods = tmp_path / "P" / "Mods"  # tmp_path/P missing: the drive is not mounted
    report = rp.release_pack("MyVest", mod, tmp_path / "out", p_mods=p_mods, date="2026-10-21")
    [warning] = [w for w in report["warnings"] if w.startswith("no-bikey")]
    assert "is not mounted" in warning and str(p_mods / "@MyVest" / "Keys") in warning
    assert "/dayz-workdrive" in warning
    (tmp_path / "P").mkdir()
    report = rp.release_pack("MyVest", mod, tmp_path / "out", p_mods=p_mods, date="2026-10-21")
    [warning] = [w for w in report["warnings"] if w.startswith("no-bikey")]
    assert "not mounted" not in warning and "sign the PBO" in warning
