#!/usr/bin/env python3
"""Local-VLM render scorer / checklist answerer for blender-visual-review.

Offloads high-frequency visual checks from the expensive agent to a FREE local
vision model served by Ollama, so agent credits are spent on gates and final
judgment, not on every inner-loop glance.

UNCALIBRATED — SHADOW MODE FIRST (LL-153): until this scorer's outputs are
shown to correlate with the agent's own verdicts on real judged iterations
(>= 15 samples), its scores are logged evidence, NEVER a gate and NEVER a
substitute for the agent's eyes. Promotion path: shadow -> pre-filter
(discard obviously-bad variants only) -> never final judge.

Modes:
  score  one render (or render vs reference) -> {"score": 0..1, "defects": [...]}
         Anchored rubric in the prompt keeps scores comparable across calls.
  ask    CADCodeVerify-style: a JSON checklist of concrete yes/no questions is
         answered from the render(s). Focused questions are measurably easier
         for small VLMs than open judgment — prefer this mode.

Both modes append a JSONL shadow-log entry with inputs, raw output and timing
(--shadow, default vr_shadow.jsonl next to the first image), which IS the
calibration dataset — no extra credit cost to build it.

Reference convergence constants from RFingAdam/mcp-blender's loop design
(score >= 0.85 accept, |delta| < 0.02 plateau) are exported for the future
pre-filter stage; they are NOT enforced here.

Requires: Ollama running (http://127.0.0.1:11434) with a vision model pulled,
e.g. gemma4:26b, qwen3.8:27b or qwen3.5:27b. Pure stdlib, Python 3.10+.
Pair mode (--reference) refuses two images of identical pixel dimensions: on qwen3.x
they collapse into one and the survivor is unpredictable (see PAIR_COLLISION_NOTE).

Usage:
    python vr_score.py score render.png --reference ref.png --model qwen3.5:27b --json
    python vr_score.py ask render.png --checklist checks.json --model gemma4:26b --json
    python vr_score.py ask --view assembled__iso iso.png --view zoom_muzzle__front_iso muzzle.png --checklist checks.json
    checks.json: [{"q": "Is the barrel cylindrical, not faceted?", "view": "zoom_muzzle__front_iso", "skip": "optional reason"}, ...]
    A view token is <subject>__<view>, matching the render filenames the Blender pass
    emits (<subject>__<view>__<subject>__<version>.png). Subject matters: 'profile' alone
    does not tell assembled__profile_L from zoom_mag__profile.
    Legacy checks.json: ["Is the barrel cylindrical, not faceted?", ...] — scored against the positional render
"""

from __future__ import annotations

import argparse
import base64
import json
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# 127.0.0.1, never "localhost": on Windows localhost resolves to ::1 first, and a stray
# IPv6-bound ollama serve will answer with a DIFFERENT (default-path) model library.
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.5:27b"
ACCEPT_SCORE = 0.85     # RFingAdam reference constants — for the future pre-filter, not enforced
PLATEAU_DELTA = 0.02
REQUEST_TIMEOUT_S = 300  # first call loads the model into VRAM; can take minutes
DEFAULT_NUM_CTX = 8192   # the factory default (262144) reserves KV cache for a context
                         # this tool never uses and pushes the model off the GPU: measured
                         # 2.3x slower on gemma4:26b, 12x on qwen3.5:27b (SP-260)
# Two images of IDENTICAL pixel dimensions COLLAPSE into one on qwen3.x VL models served by
# Ollama: prompt_eval_count bills a single image and the model describes only one of the two.
# Which one survives is not fixed -- it follows the prompt cache -- so a --reference call can
# judge the REFERENCE and never see the render, and report it as a verdict on the render.
# Measured 2026-08-16 on qwen3.5:27b and qwen3.8:27b at 8k/16k/32k num_ctx and from 558 to
# 2164 tokens per image, so it is neither a context budget nor a size budget. gemma4:26b is
# unaffected. One pixel of difference restores both images (1100x1100 + 1099x1100: both
# encoded and described, 5/5). The guard is on the images, not on the model name: an earlier
# model-name blocklist barred qwen3.5, which works fine when the sizes differ, while letting
# qwen3.8 through with the same collision.
PAIR_COLLISION_NOTE = ("identical pixel dimensions make qwen3.x collapse the two images into "
                       "one, so the verdict may describe the wrong image")

SCORE_PROMPT_PAIR = """You are a strict 3D art reviewer. Image 1 is the REFERENCE, image 2 is a RENDER of a
3D model built to match it. Judge only what is visible. Score how faithfully the render matches the
reference on: silhouette and proportions (weight 0.4), part structure and placement (0.3),
identity-defining details present and correct (0.2), surface/material plausibility (0.1).
Anchors: 0.95+ near-indistinguishable structure; 0.85 minor deviations only; 0.7 clearly same object,
several wrong details; 0.5 same category, wrong proportions or missing parts; 0.3 barely related.
Ignore background, lighting style and image quality. Reply ONLY with JSON:
{"score": <0..1>, "defects": ["<short concrete defect>", ...], "confidence": <0..1>}"""

SCORE_PROMPT_SINGLE = """You are a strict 3D art reviewer. The image is a RENDER of a game-ready hard-surface
3D model. Judge only what is visible: silhouette coherence (0.3), part connections — nothing floating or
interpenetrating (0.3), detail level — bevels, seams, hardware vs bare primitive boxes (0.2), shading
artifacts — inverted normals, pinching, z-fighting (0.2).
Anchors: 0.95+ production-quality; 0.85 solid with minor flaws; 0.7 competent but visibly unfinished;
0.5 primitive blockout; 0.3 broken geometry. Reply ONLY with JSON:
{"score": <0..1>, "defects": ["<short concrete defect>", ...], "confidence": <0..1>}"""

ASK_PROMPT = """You are inspecting a render of a 3D model. The image is the '{view}' framing. Answer each question from the visible evidence
only. If the view does not show enough to decide, answer "unsure" — do not guess.
Questions (JSON array): {questions}
Reply ONLY with JSON: {"answers": [{"q": "<question>", "answer": "yes"|"no"|"unsure",
"note": "<one short factual observation>"}, ...]}"""


def image_size(path: Path) -> tuple[int, int] | None:
    """(width, height) from a PNG or JPEG header, or None if the format is unreadable.

    Pure stdlib on purpose (this file has no third-party deps). None means "cannot
    tell", and the caller treats it as no-clash rather than as a match: refusing to
    run on an unparsed header would break formats this check has no opinion about.
    Verified against PIL on 61 renders, references and textures with no disagreement.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
                return struct.unpack(">II", head[16:24])
            if head[:2] != b"\xff\xd8":
                return None
            fh.seek(2)
            while True:
                b = fh.read(1)
                if not b:
                    return None
                if b != b"\xff":
                    continue
                marker = fh.read(1)
                while marker == b"\xff":       # fill bytes are legal before a marker
                    marker = fh.read(1)
                if not marker:
                    return None
                m = marker[0]
                if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                    continue
                seg = fh.read(2)
                if len(seg) < 2:
                    return None
                length = struct.unpack(">H", seg)[0]
                if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):    # SOF0..SOF15
                    body = fh.read(5)
                    if len(body) < 5:
                        return None
                    h, w = struct.unpack(">HH", body[1:5])
                    return w, h
                fh.seek(length - 2, 1)
    except OSError:
        return None


def ask_targets(args: argparse.Namespace) -> list[Path]:
    """Every image the reference will be paired with: the positional render and each --view."""
    targets = [args.render] if args.render is not None else []
    targets += [Path(p) for _, p in (getattr(args, "view", None) or [])]
    return targets


def find_dimension_clash(reference: Path, targets: list[Path]):
    """First target that matches the reference pixel-for-pixel in size, with that size."""
    ref_size = image_size(reference)
    if ref_size is None:
        return None
    for t in targets:
        if image_size(t) == ref_size:
            return t, ref_size
    return None


def b64_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def ollama_chat(host: str, model: str, prompt: str, images: list[Path],
                num_ctx: int = DEFAULT_NUM_CTX) -> tuple[str, float]:
    """One /api/chat call with images. Returns (raw content, elapsed seconds).

    think=False is not cosmetic: with thinking on, current models put the entire reply
    in message.thinking and return message.content EMPTY, so every call ends in a JSON
    parse error and the tool produces no verdict at all (measured 2026-08-16 on both
    judge models, SP-260).
    """
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0.1, "num_ctx": num_ctx},
        "messages": [{
            "role": "user",
            "content": prompt,
            "images": [b64_image(p) for p in images],
        }],
    }
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Ollama unreachable at {host} ({exc}). Start it (ollama serve / the Ollama app) "
            f"and check the model is pulled: ollama list"
        ) from exc
    elapsed = time.monotonic() - t0
    return body.get("message", {}).get("content", ""), elapsed


def parse_model_json(raw: str) -> dict[str, Any]:
    """Parse the model's JSON reply; salvage the outermost object if wrapped in prose."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def clamp01(v: Any) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def load_checklist(path: Path) -> list[dict[str, Any]]:
    """Normalize a checklist to [{q, view, skip?}, ...].

    The historical format is a flat array of strings. vr_calibrate still
    sweeps that way, and existing files must keep loading: a string is
    question text with view=None (routed to the positional render).
    utf-8-sig, not utf-8: PowerShell's Out-File / Set-Content -Encoding utf8
    emits a BOM on 5.1, and a checklist authored that way raised
    "Unexpected UTF-8 BOM" and killed the run. utf-8-sig reads both
    (measured 2026-08-16, SP-260).
    """
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("checklist JSON must be an array")
    items: list[dict[str, Any]] = []
    for i, entry in enumerate(data):
        if isinstance(entry, str):
            q = entry.strip()
            if not q:
                raise ValueError(f"checklist[{i}] is an empty string")
            items.append({"q": q, "view": None})
            continue
        if isinstance(entry, dict):
            q = entry.get("q")
            view = entry.get("view")
            skip = entry.get("skip")
            if not isinstance(q, str) or not q.strip():
                raise ValueError(f"checklist[{i}] needs a non-empty 'q' string")
            if view is not None and (not isinstance(view, str) or not view.strip()):
                raise ValueError(f"checklist[{i}].view must be a non-empty string if set")
            if skip is not None and (not isinstance(skip, str) or not skip.strip()):
                raise ValueError(f"checklist[{i}].skip must be a non-empty string if set")
            item = {
                "q": q.strip(),
                "view": view.strip() if isinstance(view, str) else None,
            }
            if isinstance(skip, str):
                item["skip"] = skip.strip()
            items.append(item)
            continue
        raise ValueError(f"checklist[{i}] must be a string or a {{q, view, skip?}} object")
    return items


def active_checklist(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only questions eligible for VLM prompting and scoring."""
    return [item for item in items if "skip" not in item]


def parse_views(pairs: list[list[str]] | None) -> dict[str, Path]:
    """Parse repeated `--view NAME PATH` flags into a name->file map.

    Two argv tokens, not NAME=PATH: a Windows path can contain a drive
    colon and backslashes; splitting on '=' is unnecessary once argparse
    already separates the name from the path.
    """
    views: dict[str, Path] = {}
    for pair in pairs or []:
        if len(pair) != 2:
            raise ValueError(f"--view expects NAME PATH, got {pair!r}")
        name, raw = pair[0].strip(), pair[1].strip()
        if not name or not raw:
            raise ValueError(f"--view expects NAME PATH, got {pair!r}")
        if name in views:
            raise ValueError(f"duplicate --view name {name!r}")
        views[name] = Path(raw)
    return views


def resolve_view_path(
    view: str | None,
    render: Path | None,
    named: dict[str, Path],
) -> Path:
    """Bind one checklist entry to one image.

    No --view (legacy / vr_calibrate sweep): every question uses the
    positional render, even if the entry names a framing. The view field
    is recorded on the answer but does not route. Otherwise a migrated
    checklist would make `ask foo.png` fail, and the calibrator would
    stop producing the positional answers[] it indexes.

    With --view: the name is a required key. 'render' is an alias for the
    positional path so a mixed checklist can pin some questions to the
    default file without repeating --view render <png>.
    """
    if not named:
        if render is None:
            raise ValueError("ask needs a positional render or --view NAME PATH")
        return render

    if view is None or view == "render":
        if render is not None:
            return render
        if "render" in named:
            return named["render"]
        raise ValueError(
            "this checklist entry has no view (or view 'render') but no "
            "positional render was given"
        )

    try:
        return named[view]
    except KeyError:
        given = ", ".join(sorted(named)) or "none"
        raise ValueError(
            f"checklist view {view!r} was not passed as --view {view} <png> "
            f"(given: {given})"
        ) from None


def group_indices_by_view(
    items: list[dict[str, Any]],
    render: Path | None,
    named: dict[str, Path],
) -> list[tuple[str | None, Path, list[int]]]:
    """Checklist order in, one (view, path, indices) group per framing.

    One image per Ollama call on purpose: the measured disagreement was two
    questions answered against different panels of the SAME contact sheet, so
    each framing is asked on its own image rather than as a panel of a montage.
    Grouping questions that share a framing keeps the call count at the
    number of views, not the number of questions. Without --view the
    groups collapse to one call so a migrated checklist does not multiply
    vr_calibrate's per-render cost.
    """
    groups: dict[tuple[str | None, str], list[int]] = {}
    order: list[tuple[str | None, str]] = []
    paths: dict[tuple[str | None, str], Path] = {}
    for i, item in enumerate(items):
        path = resolve_view_path(item["view"], render, named)
        # No --view: one group, one call. A migrated checklist would otherwise
        # cost N Ollama calls on the same PNG in vr_calibrate's sweep.
        key = (item["view"] if named else None, str(path))
        if key not in groups:
            groups[key] = []
            order.append(key)
            paths[key] = path
        groups[key].append(i)
    return [(key[0], paths[key], groups[key]) for key in order]


def run_score(args: argparse.Namespace) -> dict[str, Any]:
    images = [args.reference, args.render] if args.reference else [args.render]
    prompt = SCORE_PROMPT_PAIR if args.reference else SCORE_PROMPT_SINGLE
    raw, elapsed = ollama_chat(args.host, args.model, prompt, images, args.ctx)
    parsed = parse_model_json(raw)
    return {
        "mode": "score",
        "model": args.model,
        "render": str(args.render),
        "reference": str(args.reference) if args.reference else None,
        "score": clamp01(parsed.get("score")),
        "defects": [str(d) for d in parsed.get("defects", []) if str(d).strip()][:12],
        "modelConfidence": clamp01(parsed.get("confidence")),
        "elapsedS": round(elapsed, 1),
        "note": "SHADOW/uncalibrated (LL-153): evidence for calibration, not a gate. "
                "Agent eyes remain the judge.",
    }


def run_ask(args: argparse.Namespace) -> dict[str, Any]:
    items = active_checklist(load_checklist(args.checklist))
    named = parse_views(getattr(args, "view", None))
    groups = group_indices_by_view(items, args.render, named)

    pending: list[dict[str, Any] | None] = [None] * len(items)
    total_elapsed = 0.0
    for view, path, indices in groups:
        questions = [items[i]["q"] for i in indices]
        prompt = ASK_PROMPT.replace("{view}", view or "render").replace(
            "{questions}", json.dumps(questions, ensure_ascii=False)
        )
        # One image per call, plus the reference when asked for. main() has already
        # refused any pairing whose two images share pixel dimensions.
        images = ([args.reference] if args.reference else []) + [path]
        raw, elapsed = ollama_chat(args.host, args.model, prompt, images, args.ctx)
        total_elapsed += elapsed
        parsed = parse_model_json(raw)
        raw_answers = parsed.get("answers", [])
        for j, qi in enumerate(indices):
            entry = raw_answers[j] if j < len(raw_answers) and isinstance(raw_answers[j], dict) else {}
            answer = str(entry.get("answer", "unsure")).lower()
            pending[qi] = {
                "q": items[qi]["q"],
                "answer": answer if answer in ("yes", "no", "unsure") else "unsure",
                "note": str(entry.get("note", ""))[:200],
                "view": items[qi]["view"],
                "image": str(path),
            }

    answers = [a for a in pending if a is not None]
    if len(answers) != len(items):
        raise RuntimeError("internal error: ask did not fill every checklist slot")
    counts = {k: sum(1 for a in answers if a["answer"] == k) for k in ("yes", "no", "unsure")}
    if args.render is not None:
        render_out = str(args.render)
    elif groups:
        render_out = str(groups[0][1])
    else:
        render_out = ""
    return {
        "mode": "ask",
        "model": args.model,
        "render": render_out,
        "reference": str(args.reference) if args.reference else None,
        "views": {k: str(v) for k, v in named.items()} if named else None,
        "answers": answers,
        "counts": counts,
        "elapsedS": round(total_elapsed, 1),
        "note": "SHADOW/uncalibrated (LL-153): 'no' answers are attention pointers for the agent, "
                "not automatic failures.",
    }


def append_shadow(shadow_path: Path, record: dict[str, Any]) -> None:
    with open(shadow_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("render", type=Path, nargs="?", default=None,
                        help="render PNG to evaluate (optional for ask if --view is given)")
    common.add_argument("--reference", type=Path, help="reference image (photo or previous render)")
    common.add_argument("--model", default=DEFAULT_MODEL)
    common.add_argument("--host", default=DEFAULT_HOST)
    common.add_argument("--ctx", type=int, default=DEFAULT_NUM_CTX,
                        help="context window; the model default is huge and costs 2-12x speed")
    common.add_argument("--shadow", type=Path, help="JSONL shadow-log path (default: vr_shadow.jsonl next to render)")
    common.add_argument("--no-shadow", action="store_true", help="skip shadow logging")
    common.add_argument("--json", action="store_true")

    sub.add_parser("score", parents=[common], help="0-1 fidelity/quality score")
    ask = sub.add_parser("ask", parents=[common], help="answer a yes/no checklist from the render")
    ask.add_argument("--checklist", type=Path, required=True,
                     help="JSON array of question strings, or {q, view, skip?} objects")
    ask.add_argument("--view", nargs=2, action="append", default=None, metavar=("NAME", "PATH"),
                     help="named framing (repeatable): --view closeup detail.png")

    args = parser.parse_args(argv)
    if args.cmd == "score" and args.render is None:
        print("error: score requires a render PNG", file=sys.stderr)
        return 2
    if args.cmd == "ask" and args.render is None and not args.view:
        print("error: ask requires a render PNG or at least one --view NAME PATH", file=sys.stderr)
        return 2
    if args.reference:
        clash = find_dimension_clash(args.reference, ask_targets(args))
        if clash is not None:
            target, size = clash
            print(f"error: {args.reference.name} and {target.name} are both {size[0]}x{size[1]}: "
                  f"{PAIR_COLLISION_NOTE}. Re-render or resize one of them so the dimensions "
                  f"differ (one pixel is enough).", file=sys.stderr)
            return 2
    try:
        result = run_score(args) if args.cmd == "score" else run_ask(args)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.no_shadow:
        if args.shadow:
            shadow = args.shadow
        elif args.render is not None:
            shadow = args.render.parent / "vr_shadow.jsonl"
        else:
            shadow = Path(args.view[0][1]).parent / "vr_shadow.jsonl"
        record = dict(result)
        record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            append_shadow(shadow, record)
        except OSError as exc:
            print(f"warning: shadow log failed: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif result["mode"] == "score":
        print(f"score {result['score']}  (model {result['model']}, {result['elapsedS']}s)")
        for d in result["defects"]:
            print(f"  defect: {d}")
    else:
        for a in result["answers"]:
            tag = f" [{a['view']}]" if a.get("view") else ""
            print(f"[{a['answer']:>6}]{tag} {a['q']}" + (f"  — {a['note']}" if a["note"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
