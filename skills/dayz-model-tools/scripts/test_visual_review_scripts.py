"""Tests for the offline visual review scripts of dayz-model-tools: the stop policy
(correction_loop.py), the same-camera comparator (vr_delta.py), the pair guard
and view routing of vr_score.py, and the shipped checklist. No Blender, no
Ollama and no third-party package is needed: images are written with
vr_delta's own PNG writer."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"bvr_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


loop = _load("correction_loop")
delta = _load("vr_delta")
score = _load("vr_score")


def _it(fidelity: float, tags=(), reverted: bool = False) -> dict:
    return {"fidelity": fidelity, "defectTags": list(tags), "reverted": reverted}


# --- correction_loop.py -----------------------------------------------------

@pytest.mark.parametrize(
    "history, stop, action",
    [
        ([], False, "continue-iterating"),
        ([_it(0.5, ["gap"])], False, "continue-iterating"),
        ([_it(0.9)], True, "continue"),
        ([_it(0.5, ["gap"]), _it(0.6, ["gap"])], True, "refine-spec"),
        ([_it(0.5, ["a"], True), _it(0.6, ["b"], True)], True, "refine-spec"),
        ([_it(0.5, ["a"]), _it(0.4, ["b"]), _it(0.6, ["c"])], True, "refine-spec"),
        ([_it(0.5, ["a"]), _it(0.51, ["b"])], True, "request-input"),
    ],
    ids=["empty", "first", "target-met", "repeated-defect", "two-reverts", "direction-flip", "plateau"],
)
def test_stop_policy_verdicts(history, stop, action):
    decision = loop.decide(history)
    assert (decision["stop"], decision["action"]) == (stop, action)


def test_stop_policy_never_runs_past_the_ceiling():
    # Always improving, never reaching the target, a new defect tag each time:
    # only the iteration ceiling can stop this loop.
    history = []
    while not loop.decide(history)["stop"]:
        n = len(history)
        history.append(_it(0.10 + 0.05 * n, [f"defect-{n}"]))
        assert len(history) <= 6
    assert len(history) == 6
    assert loop.decide(history) == {"stop": True, "action": "request-input", "reason": "hit MAX_ITER ceiling"}


def test_stop_policy_cli_exit_codes(tmp_path, capsys):
    going = tmp_path / "going.json"
    going.write_text(json.dumps([_it(0.5, ["gap"])]), encoding="utf-8")
    done = tmp_path / "done.json"
    done.write_text(json.dumps([_it(0.9)]), encoding="utf-8")
    not_a_list = tmp_path / "bad.json"
    not_a_list.write_text("{}", encoding="utf-8")

    assert loop.main(["--history", str(going), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "continue-iterating"
    assert loop.main(["--history", str(done), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["action"] == "continue"
    assert loop.main(["--history", str(not_a_list), "--json"]) == 2
    assert "history JSON must be a list" in capsys.readouterr().out


# --- vr_delta.py ------------------------------------------------------------

def _render(path: Path, box: tuple[int, int, int, int], size: int = 64) -> Path:
    """A grey background with one dark rectangle (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    rgb = bytearray()
    for y in range(size):
        for x in range(size):
            rgb += bytes((30, 30, 30) if x0 <= x < x1 and y0 <= y < y1 else (200, 200, 200))
    delta.write_png_rgb(path, size, size, bytes(rgb))
    return path


def test_png_writer_and_reader_round_trip(tmp_path):
    path = _render(tmp_path / "a.png", (16, 16, 48, 48))
    width, height, pixels = delta.read_png(path)
    assert (width, height, len(pixels)) == (64, 64, 64 * 64)
    assert pixels[0] == (200, 200, 200, 255) and pixels[32 * 64 + 32] == (30, 30, 30, 255)


def test_same_render_twice_reports_identical_images_and_no_moved_signal(tmp_path):
    a = _render(tmp_path / "a.png", (16, 16, 48, 48))
    b = _render(tmp_path / "b.png", (16, 16, 48, 48))
    result = delta.evaluate_pair(a, b)
    assert result["identicalImages"] is True
    assert result["movedSignals"] == []
    assert result["signals"]["silhouetteIoU"] == 1.0
    assert "verdict" not in result  # report only: the tool never passes or fails an iteration


def test_a_changed_silhouette_moves_the_silhouette_and_scale_signals(tmp_path):
    before = _render(tmp_path / "before.png", (16, 16, 48, 48))
    after = _render(tmp_path / "after.png", (16, 16, 48, 32))
    result = delta.evaluate_pair(before, after)
    assert result["identicalImages"] is False
    assert result["signals"]["silhouetteIoU"] < 0.99
    assert {"silhouetteIoU", "scaleDelta", "aspectRatioDelta"} <= set(result["movedSignals"])


def test_delta_cli_exit_codes(tmp_path, capsys):
    a = _render(tmp_path / "a.png", (16, 16, 48, 48))
    not_png = tmp_path / "note.png"
    not_png.write_text("not an image", encoding="utf-8")

    assert delta.main([str(a), str(a), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["identicalImages"] is True
    assert delta.main([str(a), str(not_png), "--json"]) == 2
    assert "not a PNG file" in capsys.readouterr().err


# --- vr_score.py ------------------------------------------------------------

def test_image_size_reads_png_headers_and_gives_none_for_other_files(tmp_path):
    png = _render(tmp_path / "a.png", (1, 1, 5, 5), size=32)
    other = tmp_path / "note.txt"
    other.write_text("hello", encoding="utf-8")
    assert score.image_size(png) == (32, 32)
    assert score.image_size(other) is None
    assert score.image_size(tmp_path / "missing.png") is None


def test_reference_of_the_same_pixel_size_is_refused_before_any_model_call(tmp_path, monkeypatch, capsys):
    render = _render(tmp_path / "render.png", (16, 16, 48, 48))
    same = _render(tmp_path / "ref_same.png", (8, 8, 40, 40))
    smaller = _render(tmp_path / "ref_smaller.png", (8, 8, 40, 40), size=63)
    assert score.find_dimension_clash(same, [render]) == (render, (64, 64))
    assert score.find_dimension_clash(smaller, [render]) is None

    def no_call(*args, **kwargs):
        raise AssertionError("the model must not be called for a refused pair")

    monkeypatch.setattr(score, "ollama_chat", no_call)
    assert score.main(["score", str(render), "--reference", str(same), "--no-shadow"]) == 2
    assert "are both 64x64" in capsys.readouterr().err


def test_views_route_each_question_to_its_own_image(tmp_path):
    items = [{"q": "A?", "view": "m__iso"}, {"q": "B?", "view": "m__top"}, {"q": "C?", "view": "m__iso"}]
    named = score.parse_views([["m__iso", "iso.png"], ["m__top", "top.png"]])
    groups = score.group_indices_by_view(items, None, named)
    assert groups == [("m__iso", Path("iso.png"), [0, 2]), ("m__top", Path("top.png"), [1])]
    # Without --view every question goes to the positional render in one call.
    assert score.group_indices_by_view(items, Path("r.png"), {}) == [(None, Path("r.png"), [0, 1, 2])]
    with pytest.raises(ValueError, match="was not passed as --view m__top"):
        score.group_indices_by_view(items, None, score.parse_views([["m__iso", "iso.png"]]))
    with pytest.raises(ValueError, match="duplicate --view name"):
        score.parse_views([["m__iso", "a.png"], ["m__iso", "b.png"]])


def test_shipped_checklist_has_five_active_and_three_skipped_questions():
    # skills/_shared/models/tools-vlm-judge.md states these counts and which questions are excluded.
    items = score.load_checklist(HERE / "checks_hardsurface.json")
    active = score.active_checklist(items)
    assert (len(items), len(active)) == (8, 5)
    skipped = [item["q"] for item in items if "skip" in item]
    assert [q.split()[0:3] for q in skipped] == [
        ["Are", "cylindrical", "parts"],
        ["Are", "there", "any"],
        ["Are", "the", "proportions"],
    ]
    assert {item["view"] for item in active} == {"assembled__iso", "zoom_receiver__right_iso", "assembled__profile_L"}
