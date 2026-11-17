from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from packctl_testlib import REPO_ROOT, TOOLING_ROOT, run_git


SCRIPT = REPO_ROOT / "scripts/tools/skill-runtime-pin/runtime_pin.py"

V1_SKILL = """---
name: dayz-mod-workflow
description: V1 fixture workflow.
---

# V1 body unique-token-alpha

Read `references/error-catalog.md` when the procedure names it.
"""

V2_SKILL = """---
name: dayz-mod-workflow
description: V2 fixture workflow.
---

# V2 body unique-token-beta

Read `references/error-catalog.md` when the procedure names it.
Also `references/concurrent-session-snapshot.md`.
"""

V1_REF = "error catalog v1\n"
V2_SNAPSHOT = "concurrent snapshot v2\n"
SHARED = "shared conventions\n"


def load_pin():
    spec = importlib.util.spec_from_file_location("skill_runtime_pin", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pin(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=TOOLING_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def report_of(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(result.stdout)


def write_tree(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def pack_files(skill_body: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    files = {
        "LICENSE": "MIT\n",
        "README.md": "fixture pack\n",
        "skills/dayz-mod-workflow/SKILL.md": skill_body,
        "skills/dayz-mod-workflow/references/error-catalog.md": V1_REF,
        "skills/_shared/conventions.md": SHARED,
        "tools/dayz-script-validator/scripts/script_validator.py": "print('fixture')\n",
    }
    if extra:
        files.update(extra)
    return files


def git_commit(root: Path, message: str) -> str:
    run_git(root, "add", "-A")
    run_git(root, "commit", "-qm", message)
    return run_git(root, "rev-parse", "HEAD")


def fixture_repo(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "source"
    root.mkdir()
    write_tree(root, pack_files(V1_SKILL))
    run_git(root, "init", "-q")
    run_git(root, "config", "user.email", "fixture@example.invalid")
    run_git(root, "config", "user.name", "Fixture")
    run_git(root, "config", "core.autocrlf", "false")
    v1 = git_commit(root, "v1")
    write_tree(
        root,
        pack_files(
            V2_SKILL,
            {"skills/dayz-mod-workflow/references/concurrent-session-snapshot.md": V2_SNAPSHOT},
        ),
    )
    v2 = git_commit(root, "v2")
    return root, v1, v2


def git_blob(root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{path}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def dangling_tree_commit(root: Path, mode: str, sha: str, path: str, message: str) -> str:
    run_git(root, "update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}")
    tree = run_git(root, "write-tree")
    parent = run_git(root, "rev-parse", "HEAD")
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
    )
    commit = subprocess.run(
        ["git", "commit-tree", tree, "-p", parent, "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
        env=env,
    ).stdout.decode("ascii").strip()
    run_git(root, "read-tree", "HEAD")
    assert run_git(root, "status", "--porcelain") == ""
    return commit


def pin_mod():
    return load_pin()


def assemble_all(task: Path) -> dict[str, object]:
    assembled = run_pin("assemble", "--task-root", str(task), "--consumer", "all")
    assert assembled.returncode == 0, assembled.stderr
    return report_of(assembled)["artifacts"]["commands"]


def cursor_grade_payload(task: Path, commands: dict[str, object], **overrides) -> dict[str, object]:
    receipt = json.loads((task / "receipt.json").read_text(encoding="utf-8"))
    payload: dict[str, object] = {
        "schema_version": 1,
        "consumer": "cursor",
        "exit_code": 0,
        "stdout": receipt["canary"],
        "argv": commands["cursor"]["argv"],
        "tool_reads": [],
        "injected_bodies": [],
        "system_init": {
            "type": "system",
            "subtype": "init",
            "model": "Cursor Grok 4.6 Extra High",
        },
    }
    payload.update(overrides)
    return payload


def write_json_doc(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def test_v1_materialize_preserves_every_blob_and_writes_derived_adapter(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task-v1"
    result = run_pin(
        "materialize",
        "--source",
        str(source),
        "--commit",
        v1,
        "--task-root",
        str(task),
    )
    assert result.returncode == 0, result.stderr
    report = report_of(result)
    manifest = json.loads((task / "manifest.json").read_text(encoding="utf-8"))
    probe = task / "probe"
    tracked = run_git(source, "ls-tree", "-r", "--name-only", v1).splitlines()
    captured = {item["path"] for item in manifest["files"]}
    assert captured == set(tracked)
    for relative in tracked:
        actual = (probe / relative).read_bytes()
        expected = git_blob(source, v1, relative)
        assert actual == expected
    alias = f"dayz-mod-workflow-{v1[:7]}"
    adapter = probe / ".agents" / "skills" / alias / "SKILL.md"
    original = probe / "skills" / "dayz-mod-workflow" / "SKILL.md"
    receipt = json.loads((task / "receipt.json").read_text(encoding="utf-8"))
    assert report["artifacts"]["alias"] == alias
    assert adapter.is_file()
    assert adapter.parent.name == alias
    text = adapter.read_text(encoding="utf-8")
    assert text.splitlines()[1] == f"name: {alias}"
    assert "skills/dayz-mod-workflow/SKILL.md" in text
    assert "DERIVED" in text
    assert receipt["canary"] in text
    assert original.read_bytes() == git_blob(source, v1, "skills/dayz-mod-workflow/SKILL.md")
    assert original.read_bytes() != adapter.read_bytes()
    assert not (probe / "receipt.json").exists()
    assert (task / "receipt.json").is_file()
    assert manifest["source_commit"] == v1
    assert manifest["source_tree"] == run_git(source, "rev-parse", f"{v1}^{{tree}}")
    assert manifest["probe_tree"] == manifest["source_tree"]
    assert manifest["adapter_kind"] == "DERIVED"
    assert manifest["capture_sha256_before"] == manifest["capture_sha256_after"]
    assert receipt["nonce"] not in V1_SKILL
    assert receipt["original_git_blob"] == run_git(
        source, "rev-parse", f"{v1}:skills/dayz-mod-workflow/SKILL.md"
    )
    verify = run_pin("verify", "--task-root", str(task))
    assert verify.returncode == 0
    assert report_of(verify)["verdict"] == "PASS"


def test_v2_and_v1_rollback_restore_v1_bytes_not_v2(tmp_path: Path) -> None:
    source, v1, v2 = fixture_repo(tmp_path)
    task_v1 = tmp_path / "task-v1"
    task_v2 = tmp_path / "task-v2"
    task_v1_again = tmp_path / "task-v1-again"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task_v1)).returncode == 0
    assert run_pin("materialize", "--source", str(source), "--commit", v2, "--task-root", str(task_v2)).returncode == 0
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task_v1_again)).returncode == 0

    v1_bytes = git_blob(source, v1, "skills/dayz-mod-workflow/SKILL.md")
    v2_bytes = git_blob(source, v2, "skills/dayz-mod-workflow/SKILL.md")
    assert v1_bytes != v2_bytes
    assert (task_v1 / "probe/skills/dayz-mod-workflow/SKILL.md").read_bytes() == v1_bytes
    assert (task_v2 / "probe/skills/dayz-mod-workflow/SKILL.md").read_bytes() == v2_bytes
    assert (task_v1_again / "probe/skills/dayz-mod-workflow/SKILL.md").read_bytes() == v1_bytes
    assert (task_v1_again / "probe/skills/dayz-mod-workflow/SKILL.md").read_bytes() != v2_bytes
    assert "unique-token-beta" not in (task_v1_again / "probe/skills/dayz-mod-workflow/SKILL.md").read_text(encoding="utf-8")
    n1 = json.loads((task_v1 / "receipt.json").read_text(encoding="utf-8"))["nonce"]
    n2 = json.loads((task_v2 / "receipt.json").read_text(encoding="utf-8"))["nonce"]
    n3 = json.loads((task_v1_again / "receipt.json").read_text(encoding="utf-8"))["nonce"]
    assert len({n1, n2, n3}) == 3
    assert (task_v2 / "probe/skills/dayz-mod-workflow/references/concurrent-session-snapshot.md").read_bytes() == V2_SNAPSHOT.encode()
    assert not (task_v1 / "probe/skills/dayz-mod-workflow/references/concurrent-session-snapshot.md").exists()


def test_refuses_dirty_source_symlink_submodule_traversal_and_collision(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    (source / "README.md").write_text("dirty\n", encoding="utf-8")
    dirty = run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(tmp_path / "t-dirty"))
    assert dirty.returncode == 1
    assert report_of(dirty)["findings"][0]["code"] == "DIRTY-SOURCE"
    run_git(source, "checkout", "--", "README.md")

    link_blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=source,
        input=b"skills/dayz-mod-workflow/SKILL.md",
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip()
    symlink_commit = dangling_tree_commit(source, "120000", link_blob, "evil-link", "symlink")
    symlink = run_pin(
        "materialize",
        "--source",
        str(source),
        "--commit",
        symlink_commit,
        "--task-root",
        str(tmp_path / "t-link"),
    )
    assert symlink.returncode == 1
    assert report_of(symlink)["findings"][0]["code"] == "SYMLINK"

    submodule_commit = dangling_tree_commit(source, "160000", v1, "deps/mod", "submodule")
    gitlink = run_pin(
        "materialize",
        "--source",
        str(source),
        "--commit",
        submodule_commit,
        "--task-root",
        str(tmp_path / "t-sub"),
    )
    assert gitlink.returncode == 1
    assert report_of(gitlink)["findings"][0]["code"] == "SUBMODULE"

    traversal = run_pin(
        "materialize",
        "--source",
        str(source),
        "--commit",
        v1,
        "--task-root",
        str(tmp_path / "t-trav"),
        "--skill",
        "../escape",
    )
    assert traversal.returncode == 1
    assert report_of(traversal)["findings"][0]["code"] == "UNSAFE-SKILL"

    missing = run_pin(
        "materialize",
        "--source",
        str(source),
        "--commit",
        v1,
        "--task-root",
        str(tmp_path / "t-missing"),
        "--skill",
        "no-such-skill",
    )
    assert missing.returncode == 1
    assert report_of(missing)["findings"][0]["code"] == "MISSING-SKILL"

    exists = tmp_path / "t-exists"
    exists.mkdir()
    collision = run_pin(
        "materialize",
        "--source",
        str(source),
        "--commit",
        v1,
        "--task-root",
        str(exists),
    )
    assert collision.returncode == 1
    assert report_of(collision)["findings"][0]["code"] == "OUTPUT-COLLISION"


def test_verify_fails_on_byte_mismatch_and_removal(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    original = task / "probe/skills/dayz-mod-workflow/SKILL.md"
    original.write_bytes(original.read_bytes() + b"x")
    mismatch = report_of(run_pin("verify", "--task-root", str(task)))
    assert mismatch["verdict"] == "FAIL"
    assert {item["code"] for item in mismatch["findings"]} >= {"MISMATCH", "BLOB-MISMATCH", "MUTATION"}

    original.write_bytes(git_blob(source, v1, "skills/dayz-mod-workflow/SKILL.md"))
    (task / "probe/skills/_shared/conventions.md").unlink()
    removed = report_of(run_pin("verify", "--task-root", str(task)))
    assert removed["verdict"] == "FAIL"
    assert any(item["code"] == "REMOVAL" for item in removed["findings"])


def test_assemble_uses_measured_flags_and_keeps_nonce_out_of_prompt(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    assembled = run_pin("assemble", "--task-root", str(task), "--consumer", "all")
    assert assembled.returncode == 0, assembled.stderr
    payload = report_of(assembled)
    commands = payload["artifacts"]["commands"]
    receipt = json.loads((task / "receipt.json").read_text(encoding="utf-8"))
    alias = json.loads((task / "manifest.json").read_text(encoding="utf-8"))["alias"]
    probe = str((task / "probe").resolve())

    inspect = commands["codex"]["inspect"]["argv"]
    assert inspect == ["codex", "debug", "prompt-input", "runtime-catalog-probe"]
    exec_argv = commands["codex"]["exec"]["argv"]
    assert commands["codex"]["program"] == "codex"
    assert commands["codex"]["argv"] == exec_argv
    assert exec_argv[:8] == ["codex", "exec", "--json", "--ephemeral", "-s", "read-only", "-C", probe]
    assert "-m" in exec_argv and exec_argv[exec_argv.index("-m") + 1] == "gpt-5.6-sol"
    prompt = exec_argv[-1]
    assert prompt.startswith(f"${alias} ")
    assert "Execute its runtime canary" in prompt
    assert receipt["nonce"] not in prompt
    assert receipt["canary"] not in prompt
    assert "--ignore-user-config" not in exec_argv
    assert commands["codex"]["limits"]["ignore_user_config_isolates_home"] is False
    assert commands["codex"]["limits"]["codex_emits_system_init"] is False
    assert commands["codex"]["limits"]["served_model_observed"] is False
    assert commands["codex"]["limits"]["status"] == "DESIGN"
    assert commands["codex"]["requested_model"] == "gpt-5.6-sol"

    cursor = commands["cursor"]
    cursor_argv = cursor["argv"]
    flags = cursor["flags"]
    assert Path(cursor["program"]).name == "cursor-agent.cmd"
    assert isinstance(cursor_argv, list)
    assert "powershell" not in json.dumps(cursor).lower()
    assert "-Command" not in json.dumps(cursor)
    assert cursor_argv[-2] == "-p"
    assert cursor_argv[-1] == flags["prompt"]
    assert cursor_argv.index("--mode") < cursor_argv.index("-p")
    assert cursor_argv.index("--trust") < cursor_argv.index("-p")
    assert cursor_argv.index("--workspace") < cursor_argv.index("-p")
    assert cursor_argv[cursor_argv.index("--workspace") + 1] == probe
    assert flags["mode"] == "ask"
    assert flags["trust"] is True
    assert flags["workspace"] == probe
    assert flags["output_format"] == "stream-json"
    assert flags["model"] == "cursor-grok-4.6-xhigh"
    assert flags["prompt"].startswith(f"/{alias} ")
    assert receipt["nonce"] not in flags["prompt"]
    assert commands["cursor"]["limits"]["catalog_exclusive"] is False
    assert commands["cursor"]["limits"]["adapter_byte_identical"] is False
    assert payload["artifacts"]["prompt_contains_nonce"] is False


def test_inspect_prompt_requires_exactly_the_derived_alias_path(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    manifest = json.loads((task / "manifest.json").read_text(encoding="utf-8"))
    alias = manifest["alias"]
    adapter = (task / "probe" / manifest["adapter_path"]).resolve()
    dump = tmp_path / "prompt-input.txt"
    dump.write_text(
        (
            "Available skills:\n"
            "- name: dayz-mod-workflow\n"
            "  path: /home/user/.agents/skills/dayz-mod-workflow/SKILL.md\n"
            f"- name: {alias}\n"
            f"  path: {adapter.as_posix()}\n"
        ),
        encoding="utf-8",
        newline="\n",
    )
    ok = run_pin("inspect-prompt", "--task-root", str(task), "--prompt-input", str(dump))
    assert ok.returncode == 0, ok.stderr
    assert report_of(ok)["verdict"] == "PASS"

    dump.write_text(
        (
            "Available skills:\n"
            f"- name: {alias}\n"
            "  path: /home/user/.agents/skills/dayz-mod-workflow/SKILL.md\n"
        ),
        encoding="utf-8",
        newline="\n",
    )
    wrong = run_pin("inspect-prompt", "--task-root", str(task), "--prompt-input", str(dump))
    assert wrong.returncode == 1
    assert any(item["code"] in {"CATALOG-ALIAS-COUNT", "CATALOG-ALIAS-PATH"} for item in report_of(wrong)["findings"])

    dump.write_text("Available skills: none\n", encoding="utf-8", newline="\n")
    missing = run_pin("inspect-prompt", "--task-root", str(task), "--prompt-input", str(dump))
    assert missing.returncode == 1
    assert report_of(missing)["findings"][0]["code"] == "CATALOG-ALIAS-COUNT"


def test_grade_false_pass_without_original_and_accepts_injected_or_read(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    receipt = json.loads((task / "receipt.json").read_text(encoding="utf-8"))
    manifest = json.loads((task / "manifest.json").read_text(encoding="utf-8"))
    commands = assemble_all(task)
    canary = receipt["canary"]
    original_rel = "skills/dayz-mod-workflow/SKILL.md"

    false_pass = tmp_path / "false.json"
    write_json_doc(false_pass, cursor_grade_payload(task, commands))
    failed = run_pin("grade", "--task-root", str(task), "--transcript", str(false_pass))
    assert failed.returncode == 1
    assert any(item["code"] == "NONCE-WITHOUT-ORIGINAL" for item in report_of(failed)["findings"])

    adapter_only = tmp_path / "adapter-only.json"
    write_json_doc(
        adapter_only,
        cursor_grade_payload(task, commands, tool_reads=[manifest["adapter_path"]]),
    )
    adapter_fail = run_pin("grade", "--task-root", str(task), "--transcript", str(adapter_only))
    assert adapter_fail.returncode == 1
    assert any(item["code"] == "NONCE-WITHOUT-ORIGINAL" for item in report_of(adapter_fail)["findings"])

    read_ok = tmp_path / "read.json"
    write_json_doc(
        read_ok,
        cursor_grade_payload(
            task,
            commands,
            tool_reads=[
                original_rel,
                "skills/dayz-mod-workflow/references/error-catalog.md",
            ],
        ),
    )
    passed = run_pin("grade", "--task-root", str(task), "--transcript", str(read_ok))
    assert passed.returncode == 0, passed.stderr
    assert report_of(passed)["artifacts"]["original_consumed"] is True

    injected = tmp_path / "injected.json"
    write_json_doc(
        injected,
        cursor_grade_payload(
            task,
            commands,
            injected_bodies=[{"path": original_rel, "sha256": manifest["original_sha256"]}],
        ),
    )
    injected_ok = run_pin("grade", "--task-root", str(task), "--transcript", str(injected))
    assert injected_ok.returncode == 0
    assert report_of(injected_ok)["artifacts"]["zero_tool_calls"] is True

    oracle = tmp_path / "oracle.json"
    write_json_doc(
        oracle,
        cursor_grade_payload(
            task,
            commands,
            tool_reads=[original_rel, str((task / "receipt.json").resolve())],
        ),
    )
    forbidden = run_pin("grade", "--task-root", str(task), "--transcript", str(oracle))
    assert forbidden.returncode == 1
    assert any(item["code"] == "FORBIDDEN-READ" for item in report_of(forbidden)["findings"])

    global_copy = tmp_path / "global.json"
    write_json_doc(
        global_copy,
        cursor_grade_payload(
            task,
            commands,
            tool_reads=[
                original_rel,
                str(tmp_path / "home/.agents/skills/dayz-mod-workflow/SKILL.md"),
            ],
        ),
    )
    leaked = run_pin("grade", "--task-root", str(task), "--transcript", str(global_copy))
    assert leaked.returncode == 1
    assert any(item["code"] == "FORBIDDEN-READ" for item in report_of(leaked)["findings"])

    codex_ok = tmp_path / "codex.json"
    write_json_doc(
        codex_ok,
        {
            "schema_version": 1,
            "consumer": "codex",
            "exit_code": 0,
            "stdout": canary,
            "argv": commands["codex"]["argv"],
            "tool_reads": [original_rel],
            "injected_bodies": [],
        },
    )
    codex_passed = run_pin("grade", "--task-root", str(task), "--transcript", str(codex_ok))
    assert codex_passed.returncode == 0, codex_passed.stderr
    assert report_of(codex_passed)["artifacts"]["served_model_observed"] is False
    assert report_of(codex_passed)["artifacts"]["limits"]["codex_emits_system_init"] is False

    invented = tmp_path / "codex-init.json"
    write_json_doc(
        invented,
        {
            "schema_version": 1,
            "consumer": "codex",
            "exit_code": 0,
            "stdout": canary,
            "argv": commands["codex"]["argv"],
            "tool_reads": [original_rel],
            "injected_bodies": [],
            "system_init": {"type": "system/init", "model": "gpt-5.6-sol"},
        },
    )
    invented_fail = run_pin("grade", "--task-root", str(task), "--transcript", str(invented))
    assert invented_fail.returncode == 1
    assert any(item["code"] == "CODEX-INIT-INVENTED" for item in report_of(invented_fail)["findings"])


def test_git_blob_sha1_matches_hash_object(tmp_path: Path) -> None:
    module = pin_mod()
    data = b"blob-contract\n"
    hashed = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=data,
        check=True,
        capture_output=True,
        cwd=tmp_path,
    ).stdout.decode("ascii").strip()
    assert module.git_blob_sha1(data) == hashed


def test_assemble_refuses_mutated_capture_before_emitting_commands(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    (task / "probe/README.md").write_bytes(b"mutated\n")
    assembled = run_pin("assemble", "--task-root", str(task), "--consumer", "cursor")
    assert assembled.returncode == 1
    assert report_of(assembled)["findings"][0]["code"] == "PREFLIGHT-FAILED"


def test_assemble_argv_keeps_metacharacters_without_a_shell_string(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "$([char]0x58) task `quoted`"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    assembled = run_pin("assemble", "--task-root", str(task), "--consumer", "all")
    assert assembled.returncode == 0, assembled.stderr
    commands = report_of(assembled)["artifacts"]["commands"]
    probe = str((task / "probe").resolve())
    cursor_argv = commands["cursor"]["argv"]
    workspace = cursor_argv[cursor_argv.index("--workspace") + 1]
    assert workspace == probe
    assert "$" in workspace
    assert "`" in workspace
    assert " " in workspace
    encoded = json.dumps(commands["cursor"])
    assert "powershell" not in encoded.lower()
    assert "-Command" not in encoded
    assert commands["codex"]["argv"][commands["codex"]["argv"].index("-C") + 1] == probe


def test_inspect_prompt_rejects_foreign_root_and_accepts_skill_roots_alias(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    manifest = json.loads((task / "manifest.json").read_text(encoding="utf-8"))
    alias = manifest["alias"]
    probe = (task / "probe").resolve()
    skills_root = (probe / ".agents" / "skills").as_posix()

    alternate = tmp_path / "alternate-root.txt"
    alternate.write_text(
        f"- name: {alias}\n  path: C:/wrong/root/.agents/skills/{alias}/SKILL.md\n",
        encoding="utf-8",
        newline="\n",
    )
    wrong_root = run_pin("inspect-prompt", "--task-root", str(task), "--prompt-input", str(alternate))
    assert wrong_root.returncode == 1
    codes = {item["code"] for item in report_of(wrong_root)["findings"]}
    assert "CATALOG-ALIAS-COUNT" in codes or "CATALOG-ALIAS-PATH" in codes

    actual = tmp_path / "actual-format.txt"
    actual.write_text(
        (
            "### Skill roots\n"
            f"- `r0` = `{skills_root}`\n"
            "### Available skills\n"
            f"- {alias}: derived (file: r0/{alias}/SKILL.md)\n"
        ),
        encoding="utf-8",
        newline="\n",
    )
    ok = run_pin("inspect-prompt", "--task-root", str(task), "--prompt-input", str(actual))
    assert ok.returncode == 0, ok.stderr
    assert report_of(ok)["verdict"] == "PASS"


def test_inspect_prompt_reads_codex_raw_json_array_with_escaped_skill_text(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    manifest = json.loads((task / "manifest.json").read_text(encoding="utf-8"))
    alias = manifest["alias"]
    skills_root = ((task / "probe") / ".agents" / "skills").resolve().as_posix()
    catalog = (
        "<skills_instructions>\n"
        "### Skill roots\n"
        "- `r0` = `C:/wrong/root/.codex/skills`\n"
        "- `r1` = `C:/wrong/root/.agents/skills`\n"
        f"- `r10` = `{skills_root}`\n"
        "### Available skills\n"
        "- imagegen: Generate images (file: r0/imagegen/SKILL.md)\n"
        f"- {alias}: DERIVED task-local runtime adapter for dayz-mod-workflow "
        f"pinned at {v1[:7]}. Not the original skill. Folder name matches this "
        f"frontmatter name. Read the immutable captured SKILL.md this adapter "
        f"names. (file: r10/{alias}/SKILL.md)\n"
        "- dayz-mod-workflow: DayZ mod implementation (file: r1/dayz-mod-workflow/SKILL.md)\n"
    )
    payload = [
        {
            "type": "message",
            "role": "developer",
            "content": [{"type": "input_text", "text": catalog}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": f"${alias} Execute its runtime canary."}],
        },
    ]
    raw = tmp_path / "codex-prompt-input-raw.json"
    raw.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    encoded = raw.read_text(encoding="utf-8")
    assert "\\n### Skill roots" in encoded
    inspect = run_pin("inspect-prompt", "--task-root", str(task), "--prompt-input", str(raw))
    assert inspect.returncode == 0, inspect.stdout
    report = report_of(inspect)
    assert report["verdict"] == "PASS"
    assert report["artifacts"]["skill_roots"]["r10"] == skills_root
    assert report["artifacts"]["alias_entries"][0]["path"].endswith(f"{alias}/SKILL.md")


def test_grade_accepts_raw_cursor_system_init_and_rejects_invented_slug(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    commands = assemble_all(task)
    original_rel = "skills/dayz-mod-workflow/SKILL.md"

    real_ok = tmp_path / "cursor-real-init.json"
    write_json_doc(
        real_ok,
        cursor_grade_payload(
            task,
            commands,
            tool_reads=[original_rel],
            system_init={
                "type": "system",
                "subtype": "init",
                "model": "Cursor Grok 4.6 Extra High",
                "session_id": "fixture-session",
                "permissionMode": "default",
            },
        ),
    )
    passed = run_pin("grade", "--task-root", str(task), "--transcript", str(real_ok))
    assert passed.returncode == 0, passed.stdout
    artifacts = report_of(passed)["artifacts"]
    assert artifacts["served_model"] == "Cursor Grok 4.6 Extra High"
    assert artifacts["requested_model"] == "cursor-grok-4.6-xhigh"
    assert artifacts["served_model_observed"] is True
    assert commands["cursor"]["argv"][commands["cursor"]["argv"].index("--model") + 1] == "cursor-grok-4.6-xhigh"

    invented = tmp_path / "invented-init.json"
    write_json_doc(
        invented,
        cursor_grade_payload(
            task,
            commands,
            tool_reads=[original_rel],
            system_init={"type": "system/init", "model": "cursor-grok-4.6-xhigh"},
        ),
    )
    invented_fail = run_pin("grade", "--task-root", str(task), "--transcript", str(invented))
    assert invented_fail.returncode == 1
    assert any(item["code"] == "CURSOR-INIT-MISSING" for item in report_of(invented_fail)["findings"])

    other = tmp_path / "other-model.json"
    write_json_doc(
        other,
        cursor_grade_payload(
            task,
            commands,
            tool_reads=[original_rel],
            system_init={"type": "system", "subtype": "init", "model": "Cursor Claude 4.5"},
        ),
    )
    other_fail = run_pin("grade", "--task-root", str(task), "--transcript", str(other))
    assert other_fail.returncode == 1
    assert any(item["code"] == "CURSOR-INIT-MODEL" for item in report_of(other_fail)["findings"])


def test_grade_rejects_canary_substring_and_wrong_injected_root(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    receipt = json.loads((task / "receipt.json").read_text(encoding="utf-8"))
    manifest = json.loads((task / "manifest.json").read_text(encoding="utf-8"))
    canary = receipt["canary"]
    original_rel = "skills/dayz-mod-workflow/SKILL.md"

    bad = tmp_path / "bad-transcript.json"
    write_json_doc(
        bad,
        {
            "schema_version": 1,
            "stdout": f"prefix {canary} suffix",
            "tool_reads": [original_rel],
            "injected_bodies": [],
        },
    )
    bad_grade = run_pin("grade", "--task-root", str(task), "--transcript", str(bad))
    assert bad_grade.returncode == 1
    bad_codes = {item["code"] for item in report_of(bad_grade)["findings"]}
    assert "CANARY-MISMATCH" in bad_codes

    commands = assemble_all(task)
    wrong_injected = tmp_path / "wrong-injected.json"
    write_json_doc(
        wrong_injected,
        cursor_grade_payload(
            task,
            commands,
            injected_bodies=[
                {
                    "path": f"C:/wrong/root/{original_rel}",
                    "sha256": manifest["original_sha256"],
                }
            ],
        ),
    )
    wrong = run_pin("grade", "--task-root", str(task), "--transcript", str(wrong_injected))
    assert wrong.returncode == 1
    report = report_of(wrong)
    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["original_consumed"] is False
    assert any(item["code"] == "NONCE-WITHOUT-ORIGINAL" for item in report["findings"])


def test_verify_rejects_extra_probe_files_and_symlinks(tmp_path: Path) -> None:
    source, v1, _v2 = fixture_repo(tmp_path)
    task = tmp_path / "task"
    assert run_pin("materialize", "--source", str(source), "--commit", v1, "--task-root", str(task)).returncode == 0
    rogue = task / "probe/.cursor/rules/rogue.mdc"
    rogue.parent.mkdir(parents=True, exist_ok=True)
    rogue.write_text("rogue\n", encoding="utf-8", newline="\n")
    extra = run_pin("verify", "--task-root", str(task))
    assert extra.returncode == 1
    extra_report = report_of(extra)
    assert extra_report["verdict"] == "FAIL"
    assert any(item["code"] == "EXTRA-FILE" for item in extra_report["findings"])
    assemble = run_pin("assemble", "--task-root", str(task), "--consumer", "cursor")
    assert assemble.returncode == 1
    assert report_of(assemble)["findings"][0]["code"] == "PREFLIGHT-FAILED"
    rogue.unlink()
    assert run_pin("verify", "--task-root", str(task)).returncode == 0

    link = task / "probe" / "extra-link"
    try:
        os.symlink(task / "probe" / "README.md", link)
    except (OSError, NotImplementedError):
        pytest.skip("os.symlink is unavailable in this environment")
    linked = run_pin("verify", "--task-root", str(task))
    assert linked.returncode == 1
    assert any(item["code"] in {"SYMLINK", "REPARSE"} for item in report_of(linked)["findings"])
