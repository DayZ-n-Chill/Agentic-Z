from __future__ import annotations

import os
import stat
import tempfile
import zipfile
from pathlib import Path

from .common import (
    canonical_json_bytes,
    finding,
    git_commit,
    git_is_dirty,
    git_tracked_files,
    load_json,
    make_report,
    sha256_bytes,
    sha256_file,
)
from .validation import SOURCE_MAP_PATH, validate_repo


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _reparse_findings(root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for relative in git_tracked_files(root):
        path = root / relative
        if path.is_symlink():
            findings.append(
                finding(
                    "BUILD-REPARSE",
                    path=relative,
                    line=0,
                    message="A Git-tracked file is a symlink/reparse point.",
                    evidence=relative,
                )
            )
    return findings


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.flag_bits |= 0x800
    return info


def build_archive(root: Path, output: Path) -> dict[str, object]:
    root = Path(root).resolve()
    output = Path(output).resolve()
    findings = _reparse_findings(root)
    if git_is_dirty(root):
        findings.append(
            finding(
                "BUILD-DIRTY",
                path=".",
                line=0,
                message="The builder requires a clean Git worktree.",
                evidence="git status --porcelain is non-empty",
            )
        )
    try:
        output.relative_to(root)
        findings.append(
            finding(
                "BUILD-OUTPUT-IN-ROOT",
                path=output.as_posix(),
                line=0,
                message="The archive output must be outside the source tree.",
                evidence=str(output),
            )
        )
    except ValueError:
        pass

    validation_report = validate_repo(root)
    findings.extend(validation_report["findings"])
    if findings:
        return make_report(
            "build",
            root,
            findings,
            checks={"validate": validation_report["verdict"]},
        )

    source_map = load_json(root / SOURCE_MAP_PATH)
    payloads = sorted(
        (
            item
            for item in source_map["artifacts"]
            if item["distribution_role"] == "payload"
        ),
        key=lambda item: item["output_path"],
    )
    payload_manifest = [
        {
            "path": item["output_path"],
            "sha256": item["output_hash"],
            "license": item["license"],
        }
        for item in payloads
    ]
    manifest = {
        "schema_version": 1,
        "release_id": source_map["release_id"],
        "source_commit": git_commit(root),
        "dayz_build": source_map["dayz_build"],
        "source_map_schema": source_map["schema_version"],
        "payload_file_count": len(payloads),
        "archive_member_count": len(payloads) + 1,
        "licenses": sorted({str(item["license"]) for item in payloads}),
        "payload": payload_manifest,
    }
    manifest_bytes = canonical_json_bytes(manifest)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=output.name + ".",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=True,
        ) as archive:
            for item in payloads:
                name = str(item["output_path"])
                data = (root / name).read_bytes()
                if sha256_bytes(data) != item["output_hash"]:
                    raise RuntimeError(f"payload hash changed during build: {name}")
                archive.writestr(_zip_info(name), data)
            archive.writestr(_zip_info("manifest.json"), manifest_bytes)
            archive.comment = b""
        os.replace(temporary_path, output)
        temporary_path = None
    except Exception as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        return make_report(
            "build",
            root,
            [
                finding(
                    "BUILD-INTERNAL-ERROR",
                    path="",
                    line=0,
                    message="The deterministic archive could not be created.",
                    evidence=type(error).__name__,
                )
            ],
        )

    return make_report(
        "build",
        root,
        [],
        checks={"validate": "PASS"},
        artifacts={
            "archive_path": str(output),
            "archive_sha256": sha256_file(output),
            "payload_file_count": len(payloads),
            "archive_member_count": len(payloads) + 1,
        },
    )
