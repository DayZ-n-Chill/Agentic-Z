from __future__ import annotations

import json
from pathlib import Path

from packctl.api_index import build_index, query_index


def codes(report: dict[str, object]) -> list[str]:
    return [str(item["code"]) for item in report["findings"]]


def write_corpus(root: Path) -> None:
    source = root / "scripts/test.c"
    source.parent.mkdir(parents=True)
    source.write_text(
        "class ActiveClass\n"
        "{\n"
        "    void ActiveMethod(int value);\n"
        "}\n"
        "// class CommentedClass {}\n"
        "/*\n"
        "void CommentedMethod();\n"
        "*/\n"
        "class First\n"
        "{\n"
        "    void SharedName();\n"
        "}\n"
        "class Second\n"
        "{\n"
        "    void SharedName(string value);\n"
        "}\n",
        encoding="utf-8",
        newline="\n",
    )


def test_active_commented_missing_and_collision_contract(tmp_path: Path) -> None:
    source_root = tmp_path / "vanilla"
    index_root = tmp_path / "index"
    write_corpus(source_root)

    report = build_index(
        source_root=source_root,
        includes=["scripts"],
        output_dir=index_root,
        source_id="vanilla",
        source_revision="rev-1",
        dayz_build="1.29.0.163451",
    )

    assert report["verdict"] == "PASS"
    assert len(query_index(index_root, "ActiveClass")["records"]) == 1
    assert len(query_index(index_root, "CommentedClass")["records"]) == 0
    assert len(query_index(index_root, "CommentedMethod")["records"]) == 0
    assert len(query_index(index_root, "DoesNotExist")["records"]) == 0
    collision = query_index(index_root, "SharedName")["records"]
    assert len(collision) == 2
    assert [record["container"] for record in collision] == ["First", "Second"]


def test_index_records_preserve_source_line_and_hash(tmp_path: Path) -> None:
    source_root = tmp_path / "vanilla"
    index_root = tmp_path / "index"
    write_corpus(source_root)
    build_index(
        source_root=source_root,
        includes=["scripts"],
        output_dir=index_root,
        source_id="vanilla",
        source_revision="rev-1",
        dayz_build="1.29.0.163451",
    )

    record = query_index(index_root, "ActiveMethod")["records"][0]

    assert record["line"] == 3
    assert record["relative_path"] == "scripts/test.c"
    assert len(record["record_hash"]) == 64
    assert record["signature"] == "void ActiveMethod(int value)"


def test_include_escape_fails_closed_without_reading_canary(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "vanilla"
    source_root.mkdir()
    canary = tmp_path / "canary.c"
    canary.write_text("class MustNotAppear {}\n", encoding="utf-8")
    index_root = tmp_path / "index"

    report = build_index(
        source_root=source_root,
        includes=["../canary.c"],
        output_dir=index_root,
        source_id="vanilla",
        source_revision="rev-1",
        dayz_build="1.29.0.163451",
    )

    assert codes(report) == ["API-PATH-ESCAPE"]
    assert "MustNotAppear" not in json.dumps(report)
    assert not (index_root / "index.jsonl").exists()


def test_query_build_mismatch_fails_closed(tmp_path: Path) -> None:
    source_root = tmp_path / "vanilla"
    index_root = tmp_path / "index"
    write_corpus(source_root)
    build_index(
        source_root=source_root,
        includes=["scripts"],
        output_dir=index_root,
        source_id="vanilla",
        source_revision="rev-1",
        dayz_build="1.29.0.163451",
    )

    report = query_index(
        index_root,
        "ActiveClass",
        expected_build="1.30.0.000000",
    )

    assert codes(report) == ["API-BUILD-MISMATCH"]
    assert report["records"] == []


def test_query_schema_mismatch_fails_closed(tmp_path: Path) -> None:
    source_root = tmp_path / "vanilla"
    index_root = tmp_path / "index"
    write_corpus(source_root)
    build_index(
        source_root=source_root,
        includes=["scripts"],
        output_dir=index_root,
        source_id="vanilla",
        source_revision="rev-1",
        dayz_build="1.29.0.163451",
    )

    report = query_index(index_root, "ActiveClass", expected_schema=2)

    assert codes(report) == ["API-SCHEMA-MISMATCH"]
    assert report["records"] == []
