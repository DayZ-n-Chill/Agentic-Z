#!/usr/bin/env python3
"""Calibration runner for the local-VLM shadow scorer.

Decides — with data, not vibes — whether a local model's visual judgments track
the agent's own, and which of several models tracks them best. Until a model
passes here it stays SHADOW-only (LL-153).

Two steps:

  run    Sweep a folder of renders through one or more models (sequentially —
         a 17 GB model fills the 24 GB card, two will not co-reside) writing one
         shadow-log record per (model, render). Costs GPU time, zero credits.

  report Join those records against the agent's own verdicts (a small JSON the
         agent fills in by LOOKING at the same renders) and print per-model
         agreement: overall agreement rate, per-question agreement, the
         disagreements themselves, and 'unsure' rate.

Agreement, not accuracy: the agent's verdicts are the reference standard here,
so a model that mirrors the agent's blind spots scores well. That is acceptable
for the intended role (cheap pre-filter that defers to the agent), and NOT
acceptable as grounds for promoting the model to a gate.

Promotion rule of thumb (needs >= 15 judged renders):
  - per-question agreement >= 0.85 on a question  -> that question is delegable
  - a question the model gets wrong in a consistent direction -> keep it agent-side
  - high 'unsure' rate on a question -> the view cannot answer it; fix the capture,
    not the model.

verdicts.json format (agent-authored, one entry per render filename):
  {"assembly__profile__fixG_v1.png": {"answers": ["yes","no","unsure"],
                                      "note": "optional"}}
Answers are positional, matching the active (not skipped) checklist order.

Pure stdlib, Python 3.10+. Usage:
    python vr_calibrate.py run  --renders <dir> --checklist checks.json --models qwen3.5:27b gemma4:26b --shadow cal.jsonl
    python vr_calibrate.py report --shadow cal.jsonl --verdicts verdicts.json --checklist checks.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from vr_score import active_checklist, load_checklist

SCORER = Path(__file__).resolve().parent / "vr_score.py"
ANSWERS = ("yes", "no", "unsure")


def checklist_labels(path: Path) -> list[str]:
    """Display active labels only. Agreement itself is positional (answers[i]).

    vr_score writes {q, view, skip?} objects. The report used to slice
    questions[qi][:60], which TypeErrors on a dict — so we stringify here
    and leave the shadow-log join (Path(render).name + answers[].answer)
    untouched.
    """
    labels: list[str] = []
    for entry in active_checklist(load_checklist(path)):
        q = entry["q"]
        view = entry["view"]
        labels.append(f"{q} [{view}]" if view else q)
    return labels


def run_sweep(args: argparse.Namespace) -> int:
    renders = sorted(p for p in args.renders.iterdir()
                     if p.suffix.lower() == ".png" and not p.name.startswith("_"))
    if args.limit:
        renders = renders[: args.limit]
    if not renders:
        print(f"no PNGs found in {args.renders}", file=sys.stderr)
        return 2
    print(f"{len(renders)} renders x {len(args.models)} models = {len(renders) * len(args.models)} calls")
    failures = 0
    # Model-major order: each model is loaded into VRAM once, then reused warm.
    for model in args.models:
        for i, render in enumerate(renders, 1):
            t0 = time.monotonic()
            cmd = [sys.executable, str(SCORER), "ask", str(render),
                   "--checklist", str(args.checklist), "--model", model,
                   "--shadow", str(args.shadow), "--json"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            elapsed = time.monotonic() - t0
            status = "ok" if proc.returncode == 0 else "FAIL"
            if proc.returncode != 0:
                failures += 1
                print(f"    stderr: {proc.stderr.strip()[:200]}", file=sys.stderr)
            print(f"[{status}] {model} {i}/{len(renders)} {render.name} ({elapsed:.0f}s)")
    print(f"\ndone; {failures} failures. Shadow log: {args.shadow}")
    return 1 if failures else 0


def load_shadow(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def report(args: argparse.Namespace) -> int:
    questions = checklist_labels(args.checklist)
    verdicts = json.loads(args.verdicts.read_text(encoding="utf-8"))
    records = [r for r in load_shadow(args.shadow) if r.get("mode") == "ask"]
    if not records:
        print("no 'ask' records in the shadow log", file=sys.stderr)
        return 2

    by_model: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_model.setdefault(rec["model"], []).append(rec)

    judged = set(verdicts)
    print(f"checklist: {len(questions)} questions | agent-judged renders: {len(judged)}")
    if len(judged) < 15:
        print(f"WARNING: {len(judged)} judged renders is below the 15 needed to promote "
              f"anything out of shadow mode — treat the numbers below as provisional.")

    for model, recs in sorted(by_model.items()):
        matched = [r for r in recs if Path(r["render"]).name in judged]
        print(f"\n=== {model} — {len(matched)}/{len(recs)} records with an agent verdict ===")
        if not matched:
            continue
        per_q_hits = [0] * len(questions)
        per_q_total = [0] * len(questions)
        unsure = [0] * len(questions)
        disagreements: list[str] = []
        stale: list[str] = []
        times: list[float] = []
        for rec in matched:
            name = Path(rec["render"]).name
            mine = verdicts[name]["answers"]
            theirs = [a["answer"] for a in rec["answers"]]
            if len(mine) != len(questions):
                stale.append(f"{name}: {len(mine)} answers vs {len(questions)} active questions")
                continue
            times.append(float(rec.get("elapsedS", 0)))
            for qi in range(min(len(questions), len(mine), len(theirs))):
                per_q_total[qi] += 1
                if theirs[qi] == "unsure":
                    unsure[qi] += 1
                if theirs[qi] == mine[qi]:
                    per_q_hits[qi] += 1
                else:
                    disagreements.append(
                        f"  {name} Q{qi + 1}: agent={mine[qi]} model={theirs[qi]} | {questions[qi][:60]}")
        if stale:
            print(f"  WARNING: {len(stale)} verdict file(s) do not match the active question "
                  f"count and were skipped. Positions moved when entries gained 'skip'; "
                  f"re-judge those renders instead of trusting a truncated comparison.")
            for line in stale[:5]:
                print(f"    {line}")
        total_hits, total_n = sum(per_q_hits), sum(per_q_total)
        rate = total_hits / total_n if total_n else 0.0
        median_t = sorted(times)[len(times) // 2] if times else 0.0
        print(f"overall agreement: {total_hits}/{total_n} = {rate:.2f} | median call {median_t:.0f}s")
        for qi, q in enumerate(questions):
            if not per_q_total[qi]:
                continue
            r = per_q_hits[qi] / per_q_total[qi]
            flag = "DELEGABLE" if r >= 0.85 else ("agent-side" if r < 0.7 else "borderline")
            print(f"  Q{qi + 1} {r:.2f} ({per_q_hits[qi]}/{per_q_total[qi]}, unsure {unsure[qi]}) "
                  f"[{flag}] {q[:58]}")
        if disagreements:
            print(f"  disagreements ({len(disagreements)}):")
            for d in disagreements[:25]:
                print(d)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="sweep renders through models into a shadow log")
    run.add_argument("--renders", type=Path, required=True)
    run.add_argument("--checklist", type=Path, required=True)
    run.add_argument("--models", nargs="+", default=["qwen3.5:27b"])
    run.add_argument("--shadow", type=Path, required=True)
    run.add_argument("--limit", type=int, help="only the first N renders")

    rep = sub.add_parser("report", help="agreement report vs the agent's verdicts")
    rep.add_argument("--shadow", type=Path, required=True)
    rep.add_argument("--verdicts", type=Path, required=True)
    rep.add_argument("--checklist", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        return run_sweep(args) if args.cmd == "run" else report(args)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
