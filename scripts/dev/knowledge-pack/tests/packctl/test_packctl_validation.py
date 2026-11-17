from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from packctl_testlib import (
    ZERO_COMMIT,
    artifact,
    make_source_map,
    require_tree_root,
    run_git,
    source,
    write_json,
)

from packctl.common import git_tracked_files
from packctl.validation import (
    validate_claims,
    validate_conflict_markers,
    validate_licenses,
    validate_links,
    validate_moved_exact,
    validate_privacy,
    validate_repo,
    validate_skills,
    validate_source_map,
)


def codes(findings: list[dict[str, object]]) -> list[str]:
    return [str(finding["code"]) for finding in findings]


def test_repository_checkout_contract_is_canonical_lf() -> None:
    # Checks the original pack tree (its .gitattributes and every path its source
    # map lists), which is not part of this repository.
    root = require_tree_root(".gitattributes", "sources/source-map.json")
    assert (root / ".gitattributes").read_bytes() == (
        b"* text eol=lf\n"
        b"*.p3d binary\n"
        b"*.rtm binary\n"
        b"*.seanim binary\n"
    )
    source_map = json.loads(
        (root / "sources/source-map.json").read_text(encoding="utf-8")
    )
    binary_suffixes = {".p3d", ".rtm", ".seanim"}
    crlf_paths = [
        str(item["output_path"])
        for item in source_map["artifacts"]
        if Path(str(item["output_path"])).suffix not in binary_suffixes
        if b"\r\n" in (root / str(item["output_path"])).read_bytes()
    ]

    assert crlf_paths == []


def test_source_clean_maps_every_tracked_file_once(repo_factory) -> None:
    root = repo_factory()

    assert validate_source_map(root) == []


def test_source_unmapped_has_stable_code(repo_factory) -> None:
    root = repo_factory()
    extra = root / "tracked-extra.txt"
    extra.write_text("unmapped\n", encoding="utf-8")

    run_git(root, "add", "tracked-extra.txt")

    assert codes(validate_source_map(root)) == ["SOURCE-UNMAPPED"]


def test_source_receipt_on_disk_must_be_mapped(repo_factory) -> None:
    root = repo_factory()
    receipt_path = "promotions/receipts/untracked.json"
    receipt = root / receipt_path
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}\n", encoding="utf-8")

    assert validate_source_map(root) == [
        {
            "code": "SOURCE-RECEIPT-UNTRACKED",
            "severity": "error",
            "path": receipt_path,
            "line": 0,
            "message": "A promotion receipt has no source-map artifact.",
            "evidence": receipt_path,
        }
    ]


def test_source_conflict_with_two_adopted_hashes_is_undecided(
    repo_factory,
) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    target = next(
        item for item in value["artifacts"] if item["output_path"] == "README.md"
    )
    target["inputs"].append(
        {
            **target["inputs"][0],
            "source_id": "other",
            "source_hash": "f" * 64,
            "decision_evidence": "Second source also marked authoritative.",
        }
    )
    value["sources"].append(source("other"))
    write_json(source_map_path, value)

    assert "SOURCE-CONFLICT-UNDECIDED" in codes(validate_source_map(root))


def test_excluded_input_cannot_overlap_an_artifact_input(repo_factory) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    source_input = value["artifacts"][0]["inputs"][0]
    value["excluded_inputs"].append(
        {
            "source_id": source_input["source_id"],
            "source_revision": source_input["source_revision"],
            "source_path": source_input["source_path"],
            "source_hash": source_input["source_hash"],
            "reason": "superseded",
            "decision_evidence": "Deliberate overlap fixture.",
        }
    )
    write_json(source_map_path, value)

    assert "SOURCE-INPUT-DUPLICATE" in codes(validate_source_map(root))


def test_source_map_rejects_private_physical_root(repo_factory) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    value["sources"][0]["physical_path"] = "C:\\Users\\person\\private"
    write_json(source_map_path, value)

    assert "SOURCE-SCHEMA-INVALID" in codes(validate_source_map(root))


def test_skill_clean_description_and_allowed_frontmatter(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\n"
                "name: demo\n"
                "description: Use for a clean fixture.\n"
                "license: MIT\n"
                "compatibility: DayZ 1.29\n"
                "metadata:\n"
                "  owner: fixture\n"
                "allowed-tools: shell\n"
                "---\n"
                "# Demo\n"
            )
        }
    )

    assert validate_skills(root) == []


def test_skill_description_1025_fails(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: " + ("x" * 1025) + "\n---\n# Demo\n"
            )
        }
    )

    assert codes(validate_skills(root)) == ["SKILL-DESCRIPTION-TOO-LONG"]


def test_skill_extra_frontmatter_fails(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\n"
                "name: demo\n"
                "description: Clean description.\n"
                "invented-field: false\n"
                "---\n"
            )
        }
    )

    assert codes(validate_skills(root)) == ["SKILL-FRONTMATTER-UNSUPPORTED"]


def test_links_broken_but_fenced_example_is_ignored(repo_factory) -> None:
    root = repo_factory(
        {
            "docs/links.md": (
                "[good](../README.md)\n\n"
                "```markdown\n[fixture](does-not-exist.md)\n```\n"
            )
        }
    )

    assert validate_links(root) == []


def test_links_broken_outside_fence_fails(repo_factory) -> None:
    root = repo_factory({"docs/links.md": "[broken](does-not-exist.md)\n"})

    assert codes(validate_links(root)) == ["LINK-BROKEN"]


def test_exact_context_link_allowlist_suppresses_only_declared_target(
    repo_factory,
) -> None:
    root = repo_factory(
        {
            "docs/links.md": (
                "[private context](../private/session.md)\n"
                "[still broken](other.md)\n"
            ),
            "sources/link-allowlist.json": (
                '{\n'
                '  "schema_version": 1,\n'
                '  "entries": [\n'
                '    {\n'
                '      "path": "docs/links.md",\n'
                '      "target": "../private/session.md",\n'
                '      "reason": "Private context is intentionally not distributed."\n'
                '    }\n'
                '  ]\n'
                '}\n'
            ),
        }
    )

    findings = validate_links(root)

    assert codes(findings) == ["LINK-BROKEN"]
    assert findings[0]["evidence"] == "other.md"


def test_private_absolute_path_is_rejected(repo_factory) -> None:
    root = repo_factory({"notes.md": "Open C:\\Users\\alice\\private\\file.txt\n"})

    assert codes(validate_privacy(root)) == ["PRIVACY-PRIVATE-PATH"]


def test_privacy_rejects_flattened_private_user_path_after_placeholder(
    repo_factory,
) -> None:
    root = repo_factory(
        {
            "notes.md": (
                "SCR=r'C:\\Users\\<you>\\AppData\\Local\\Temp\\claude\\"
                "C--Users-alice-OneDrive-Documents-DayZ-Projects\\"
                "<session-id>\\scratchpad'\n"
            )
        }
    )

    assert codes(validate_privacy(root)) == ["PRIVACY-PRIVATE-PATH"]


def test_privacy_allows_public_user_placeholder(repo_factory) -> None:
    root = repo_factory(
        {
            "notes.md": (
                "SCR=r'C:\\Users\\<you>\\AppData\\Local\\Temp\\claude\\"
                "C--Users-<you>-Documents-DayZ-Projects\\"
                "<session-id>\\scratchpad'\n"
            )
        }
    )

    assert validate_privacy(root) == []


def test_private_path_in_repo_only_public_contract_is_rejected(
    repo_factory,
) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    value["sources"][0]["notes"] = "C:\\Users\\alice\\private"
    write_json(source_map_path, value)

    assert codes(validate_privacy(root)) == ["PRIVACY-PRIVATE-PATH"]


def test_secret_finding_redacts_the_value(repo_factory) -> None:
    token = "ghp_" + ("a" * 36)
    root = repo_factory({"notes.md": f"token={token}\n"})

    findings = validate_privacy(root)

    assert codes(findings) == ["PRIVACY-SECRET"]
    assert token not in json.dumps(findings)
    assert "[REDACTED]" in json.dumps(findings)


@pytest.mark.parametrize(
    "secret_line",
    [
        "-----BEGIN PRIVATE KEY-----",
        'password = "this-is-a-real-literal-secret"',
        "api_key: '0123456789abcdef0123456789abcdef'",
    ],
)
def test_privacy_rejects_private_keys_and_literal_credentials(
    repo_factory,
    secret_line: str,
) -> None:
    root = repo_factory(
        {"notes.md": secret_line + "\n"},
        payload={"LICENSE", "README.md", "notes.md"},
    )

    findings = validate_privacy(root)

    assert [item["code"] for item in findings] == ["PRIVACY-SECRET"]
    assert findings[0]["evidence"] == "[REDACTED]"
    assert secret_line not in json.dumps(findings)


def test_license_missing_fails(repo_factory) -> None:
    root = repo_factory()
    (root / "LICENSE").unlink()

    assert "LICENSE-MISSING" in codes(validate_licenses(root))


def test_forbidden_payload_license_fails(repo_factory) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    target = next(
        item for item in value["artifacts"] if item["output_path"] == "README.md"
    )
    target["license"] = "GPL-3.0-only"
    write_json(source_map_path, value)

    assert "LICENSE-FORBIDDEN-PAYLOAD" in codes(validate_licenses(root))


def test_claim_registry_requires_marker_and_exact_range(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Demo.\n---\n"
                "[EXACT][CLAIM-DEMO-API] Call `Demo()`.\n"
            )
        }
    )
    claims = {
        "schema_version": 1,
        "claim_baseline_commit": ZERO_COMMIT,
        "claims": [
            {
                "claim_id": "CLAIM-DEMO-API",
                "artifact_id": "skills-demo-SKILL-md",
                "line_start": 5,
                "line_end": 5,
                "source_id": "pack",
                "source_revision": ZERO_COMMIT,
                "evidence_locator": "fixture.c:1",
                "license": "MIT",
                "observed_at": "2026-07-24",
                "verification_level": "source_verified",
                "promotion_artifact_id": "fixture",
            }
        ],
    }
    write_json(root / "sources/claims.json", claims)

    assert validate_claims(root) == []


def test_claim_registry_ignores_repo_only_contract_examples(repo_factory) -> None:
    root = repo_factory(
        {
            "specs/example.md": (
                "Example syntax: [EXACT][CLAIM-EXAMPLE-ONLY]\n"
            )
        },
        payload={"LICENSE", "README.md"},
    )

    assert validate_claims(root) == []


def test_unregistered_exact_claim_fails(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Demo.\n---\n"
                "[EXACT][CLAIM-MISSING] Call `Missing()`.\n"
            )
        }
    )

    assert codes(validate_claims(root)) == ["CLAIM-UNREGISTERED"]


SEAL_BODY = "1. **A moved passage.** Verbatim, byte for byte.\n"


def _sha_of(body: str) -> str:
    import hashlib

    return hashlib.sha256(body.encode("utf-8")).hexdigest().upper()


def _seal(tmp_path: Path, sha: str, body: str, close: bool = True) -> Path:
    skill = tmp_path / "skills" / "demo"
    skill.mkdir(parents=True)
    text = (
        "# Demo\n\n"
        f'<!-- MOVED-EXACT source="other/SKILL.md:12" sha256="{sha}" -->\n'
        f"{body}"
    )
    if close:
        text += "<!-- END MOVED-EXACT -->\n"
    target = skill / "notes.md"
    target.write_bytes(text.encode("utf-8"))
    return target


def test_moved_exact_seal_that_matches_its_body_is_silent(tmp_path: Path) -> None:
    _seal(tmp_path, _sha_of(SEAL_BODY), SEAL_BODY)
    assert codes(validate_moved_exact(tmp_path)) == []


def test_moved_exact_seal_reports_a_body_edited_after_sealing(tmp_path: Path) -> None:
    # The measured failure: a rename sweep edited the body and the pin stayed put.
    edited = SEAL_BODY.replace("moved", "renamed")
    _seal(tmp_path, _sha_of(SEAL_BODY), edited)
    findings = validate_moved_exact(tmp_path)
    assert codes(findings) == ["SKILL-MOVED-EXACT-DRIFT"]
    evidence = str(findings[0]["evidence"])
    assert _sha_of(SEAL_BODY)[:12] in evidence
    assert _sha_of(edited)[:12] in evidence
    assert findings[0]["path"] == "skills/demo/notes.md"


def test_moved_exact_missing_close_marker_is_reported_not_skipped(tmp_path: Path) -> None:
    # Without this, deleting the closing marker would exempt a block instead of failing it.
    _seal(tmp_path, _sha_of(SEAL_BODY), SEAL_BODY, close=False)
    assert codes(validate_moved_exact(tmp_path)) == ["SKILL-MOVED-EXACT-UNCLOSED"]


def test_moved_exact_pin_comparison_ignores_hex_case(tmp_path: Path) -> None:
    _seal(tmp_path, _sha_of(SEAL_BODY).lower(), SEAL_BODY)
    assert codes(validate_moved_exact(tmp_path)) == []


def test_every_moved_exact_seal_in_this_repo_matches_its_body() -> None:
    root = Path(__file__).resolve().parents[2]
    assert codes(validate_moved_exact(root)) == []


# What `git merge` writes with merge.conflictStyle=diff3 (zdiff3 writes the same
# markers): the plain style is this without the two base lines.
CONFLICT_BLOCK = (
    "<<<<<<< HEAD\n"
    "ours\n"
    "||||||| 224d81d\n"
    "base\n"
    "=======\n"
    "theirs\n"
    ">>>>>>> 4de8b5a1a84d6efdf81293d5c83d9cabaafef204\n"
)


def test_conflict_markers_are_reported_line_by_line(repo_factory) -> None:
    # The measured failure: the squash of #52 committed three of these into
    # CHANGELOG.md, and validate passed with 0 findings.
    root = repo_factory({"CHANGELOG.md": "# Changelog\n\n" + CONFLICT_BLOCK})

    findings = validate_conflict_markers(root)

    assert codes(findings) == ["MERGE-CONFLICT-MARKER"] * 4
    assert [(item["path"], item["line"]) for item in findings] == [
        ("CHANGELOG.md", 3),
        ("CHANGELOG.md", 5),
        ("CHANGELOG.md", 7),
        ("CHANGELOG.md", 9),
    ]
    assert findings[3]["evidence"] == (
        ">>>>>>> 4de8b5a1a84d6efdf81293d5c83d9cabaafef204"
    )


def test_conflict_markers_count_inside_fences_and_in_any_text_file(
    repo_factory,
) -> None:
    root = repo_factory(
        {
            "docs/example.md": (
                "```python\n"
                "<<<<<<< ours\n"
                "x = 1\n"
                "=======\n"
                "x = 2\n"
                ">>>>>>> theirs\n"
                "```\n"
            ),
            "ui/menu.layout": "FrameWidgetClass root {\n<<<<<<<\tours\n}\n",
            "scripts/run.sh": (
                "<<<<<<<\r\necho one\r\n=======\r\necho two\r\n>>>>>>>\r\n"
            ),
        }
    )

    findings = validate_conflict_markers(root)

    assert [(item["path"], item["line"]) for item in findings] == [
        ("docs/example.md", 2),
        ("docs/example.md", 4),
        ("docs/example.md", 6),
        ("scripts/run.sh", 1),
        ("scripts/run.sh", 3),
        ("scripts/run.sh", 5),
        ("ui/menu.layout", 2),
    ]


def test_conflict_separators_count_only_inside_a_hunk(repo_factory) -> None:
    root = repo_factory(
        {
            "notes.md": (
                "Example\n"
                "=======\n"
                "\n"
                "<<<<<<< ours\n"
                "a\n"
                "========\n"
                "=======\n"
                "b\n"
                ">>>>>>> theirs\n"
                "=======\n"
                "|||||||\n"
                ">>>>>>> left behind\n"
            ),
        }
    )

    findings = validate_conflict_markers(root)

    # The setext underline before the hunk, the 8-character run inside it and
    # the separators after it pass; a closing marker counts without its opener.
    assert [item["line"] for item in findings] == [4, 7, 9, 12]


def test_conflict_marker_lookalikes_are_not_reported(repo_factory) -> None:
    root = repo_factory(
        {
            "notes.md": (
                "A ruler as long as skills/dayz-pbo-build/SKILL.md:337 has\n"
                "=================================\n"
                "<<<<<<<< eight\n"
                ">>>>>>>>>> ten\n"
                "<<<<<<<HEAD\n"
                "> > > a nested quote\n"
                "  <<<<<<< indented, as a document shows one\n"
                "| a | b |\n"
            ),
        }
    )

    assert validate_conflict_markers(root) == []


def test_conflict_markers_skip_untracked_and_binary_files(repo_factory) -> None:
    root = repo_factory()
    block = CONFLICT_BLOCK.encode("utf-8")
    (root / "untracked.md").write_bytes(block)
    # Git's binary test: a NUL byte among the first 8000 bytes.
    (root / "binary.p3d").write_bytes(b"x" * 7999 + b"\0\n" + block)
    (root / "text.dat").write_bytes(b"x" * 8000 + b"\0\n" + block)
    run_git(root, "add", "binary.p3d", "text.dat")

    findings = validate_conflict_markers(root)

    assert [(item["path"], item["line"]) for item in findings] == [
        ("text.dat", 2),
        ("text.dat", 4),
        ("text.dat", 6),
        ("text.dat", 8),
    ]


def test_conflict_markers_read_bytes_and_number_lines_as_git_does(
    repo_factory,
) -> None:
    # A form feed, a lone CR and U+2028 end lines for str.splitlines() and the
    # text reader, not for git; a Latin-1 file is text to git too.
    root = repo_factory({"notes.md": "one\x0ctwo\rthree four\n" + CONFLICT_BLOCK})
    (root / "latin1.cfg").write_bytes(b"caf\xe9\n" + CONFLICT_BLOCK.encode("utf-8"))
    run_git(root, "add", "latin1.cfg")

    findings = validate_conflict_markers(root)

    assert [(item["path"], item["line"]) for item in findings] == [
        ("latin1.cfg", 2),
        ("latin1.cfg", 4),
        ("latin1.cfg", 6),
        ("latin1.cfg", 8),
        ("notes.md", 2),
        ("notes.md", 4),
        ("notes.md", 6),
        ("notes.md", 8),
    ]


def test_conflict_markers_on_a_last_line_without_line_feed(repo_factory) -> None:
    root = repo_factory(
        {
            "alone.md": "text\n<<<<<<< HEAD",
            "open.md": "<<<<<<< ours\na\n=======",
        }
    )

    findings = validate_conflict_markers(root)

    assert [(item["path"], item["line"]) for item in findings] == [
        ("alone.md", 2),
        ("open.md", 1),
        ("open.md", 3),
    ]


def test_conflict_markers_of_an_unmerged_path_are_reported_once(
    repo_factory,
) -> None:
    # During an unresolved merge, git ls-files lists the path once per stage.
    root = repo_factory({"notes.md": "base\n"})
    ours = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    theirs = ours + "-theirs"
    run_git(root, "checkout", "-q", "-b", theirs)
    (root / "notes.md").write_text("theirs\n", encoding="utf-8", newline="\n")
    run_git(root, "commit", "-qam", "theirs")
    run_git(root, "checkout", "-q", ours)
    (root / "notes.md").write_text("ours\n", encoding="utf-8", newline="\n")
    run_git(root, "commit", "-qam", "ours")
    with pytest.raises(subprocess.CalledProcessError):
        run_git(
            root, "-c", "merge.conflictStyle=merge", "-c", "merge.ff=false",
            "merge", theirs,
        )
    # The premise: the conflicted path sits in the index once per stage.
    assert len(run_git(root, "ls-files", "-u").splitlines()) == 3

    findings = validate_conflict_markers(root)

    assert [(item["path"], item["line"]) for item in findings] == [
        ("notes.md", 1),
        ("notes.md", 3),
        ("notes.md", 5),
    ]


def leave_unresolved_merge(root: Path, path: str, ours: str, theirs: str) -> None:
    # Each side commits its own text for *path*, then merging theirs stops on
    # the conflict, as an interrupted `git merge` leaves a worktree.
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    run_git(root, "checkout", "-q", "-b", branch + "-theirs")
    (root / path).write_text(theirs, encoding="utf-8", newline="\n")
    run_git(root, "commit", "-qam", "theirs")
    run_git(root, "checkout", "-q", branch)
    (root / path).write_text(ours, encoding="utf-8", newline="\n")
    run_git(root, "commit", "-qam", "ours")
    with pytest.raises(subprocess.CalledProcessError):
        run_git(
            root, "-c", "merge.conflictStyle=merge", "-c", "merge.ff=false",
            "merge", branch + "-theirs",
        )


def test_git_tracked_files_lists_an_unmerged_path_once(repo_factory) -> None:
    root = repo_factory({"notes.md": "base\n"})
    leave_unresolved_merge(root, "notes.md", "ours\n", "theirs\n")
    # The premise: git ls-files prints the path once per index stage.
    assert run_git(root, "ls-files").splitlines().count("notes.md") == 3

    tracked = git_tracked_files(root)

    assert tracked.count("notes.md") == 1
    assert tracked == sorted(set(run_git(root, "ls-files").splitlines()))


def test_a_broken_link_in_an_unmerged_file_is_reported_once(repo_factory) -> None:
    root = repo_factory({"notes.md": "[missing](missing.md)\nbase\n"})
    leave_unresolved_merge(
        root,
        "notes.md",
        "[missing](missing.md)\nours\n",
        "[missing](missing.md)\ntheirs\n",
    )

    findings = validate_links(root)

    assert [(item["code"], item["path"], item["line"]) for item in findings] == [
        ("LINK-BROKEN", "notes.md", 1),
    ]


def test_validate_repo_fails_on_a_conflict_marker(repo_factory) -> None:
    root = repo_factory({"CHANGELOG.md": "# Changelog\n\n" + CONFLICT_BLOCK})

    report = validate_repo(root)

    assert report["verdict"] == "FAIL"
    assert report["checks"]["conflict_markers"] == {
        "finding_count": 4,
        "verdict": "FAIL",
    }
