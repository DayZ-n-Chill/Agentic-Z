from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


REFERENCES = Path(__file__).resolve().parent  # vr_score.py and vr_calibrate.py sit next to this test


def load_module(name: str, filename: str):
    # vr_calibrate imports vr_score at module level; without the scripts dir on
    # sys.path that only resolves when another test happened to load it first.
    if str(REFERENCES) not in sys.path:
        sys.path.insert(0, str(REFERENCES))
    spec = importlib.util.spec_from_file_location(name, REFERENCES / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_skipped_question_is_neither_sent_nor_scored(tmp_path, monkeypatch):
    vr_score = load_module("vr_score", "vr_score.py")
    vr_calibrate = load_module("vr_calibrate", "vr_calibrate.py")
    reason = "Measured mechanically; no visible signal."
    checklist = tmp_path / "checks.json"
    checklist.write_text(
        json.dumps(
            [
                {"q": "Never ask this", "view": "detail", "skip": reason},
                {"q": "Ask this", "view": "detail"},
            ]
        ),
        encoding="utf-8",
    )
    prompts: list[str] = []

    def fake_ollama_chat(host, model, prompt, images, num_ctx):
        prompts.append(prompt)
        questions = json.loads(
            prompt.split("Questions (JSON array): ", 1)[1].split("\nReply ONLY", 1)[0]
        )
        return json.dumps(
            {"answers": [{"q": q, "answer": "yes", "note": "visible"} for q in questions]}
        ), 0.1

    monkeypatch.setattr(vr_score, "ollama_chat", fake_ollama_chat)
    args = argparse.Namespace(
        checklist=checklist,
        view=None,
        render=tmp_path / "render.png",
        reference=None,
        host="http://127.0.0.1:11434",
        model="test-model",
        ctx=8192,
    )

    result = vr_score.run_ask(args)

    assert "Never ask this" not in "\n".join(prompts)
    assert [answer["q"] for answer in result["answers"]] == ["Ask this"]
    assert vr_score.load_checklist(checklist)[0]["skip"] == reason
    assert vr_calibrate.checklist_labels(checklist) == ["Ask this [detail]"]


def test_legacy_flat_string_checklist_still_loads_with_bom(tmp_path):
    vr_score = load_module("vr_score", "vr_score.py")
    checklist = tmp_path / "legacy.json"
    checklist.write_text('\ufeff["First check", "Second check"]', encoding="utf-8")

    assert vr_score.load_checklist(checklist) == [
        {"q": "First check", "view": None},
        {"q": "Second check", "view": None},
    ]


def _checklist_with_one_skip(tmp_path: Path) -> Path:
    entries = [
        {"q": "Q1?", "view": "a__iso"},
        {"q": "Q2?", "view": "a__iso", "skip": "no signal in the capture"},
        {"q": "Q3?", "view": "a__iso"},
    ]
    path = tmp_path / "checks.json"
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return path


def test_report_refuses_a_verdicts_file_written_before_the_skips(tmp_path, capsys):
    # Positions used to mean the full list and now mean the active one. Truncating with
    # min() would compare Q3 of the old file against Q3 of the active list, which is a
    # different question. A count mismatch has to be loud.
    vr_calibrate = load_module("vr_calibrate", "vr_calibrate.py")
    checklist = _checklist_with_one_skip(tmp_path)

    verdicts = tmp_path / "verdicts.json"
    verdicts.write_text(
        json.dumps({"r.png": {"answers": ["yes", "no", "yes"]}}), encoding="utf-8"
    )
    shadow = tmp_path / "cal.jsonl"
    shadow.write_text(
        json.dumps(
            {
                "mode": "ask",
                "model": "m:1",
                "render": "r.png",
                "elapsedS": 1,
                "answers": [{"q": "Q1?", "answer": "yes"}, {"q": "Q3?", "answer": "yes"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    args = argparse.Namespace(checklist=checklist, verdicts=verdicts, shadow=shadow)
    vr_calibrate.report(args)
    out = capsys.readouterr().out
    assert "do not match the active question count" in out
    assert "r.png: 3 answers vs 2 active questions" in out
    assert "overall agreement: 0/0" in out


def test_report_scores_a_verdicts_file_that_matches_the_active_count(tmp_path, capsys):
    vr_calibrate = load_module("vr_calibrate", "vr_calibrate.py")
    checklist = _checklist_with_one_skip(tmp_path)

    verdicts = tmp_path / "verdicts.json"
    verdicts.write_text(
        json.dumps({"r.png": {"answers": ["yes", "yes"]}}), encoding="utf-8"
    )
    shadow = tmp_path / "cal.jsonl"
    shadow.write_text(
        json.dumps(
            {
                "mode": "ask",
                "model": "m:1",
                "render": "r.png",
                "elapsedS": 1,
                "answers": [{"q": "Q1?", "answer": "yes"}, {"q": "Q3?", "answer": "yes"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    args = argparse.Namespace(checklist=checklist, verdicts=verdicts, shadow=shadow)
    vr_calibrate.report(args)
    out = capsys.readouterr().out
    assert "do not match the active question count" not in out
    assert "overall agreement: 2/2" in out
