"""/dayz-route: pick the skill, agent or team for a DayZ request without a model turn when possible.

Stage 1 matches rules.json (free). Stage 2 asks TypeSafe's Jev (jev.py), only when
TYPESAFE_API_KEY is set. When neither is confident, the answer is
{"route": null, "next": "dayz-router"} and the caller asks the Haiku dayz-router agent.

Usage: python route.py "<request>" [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Mapping, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import skill_helpers as h  # noqa: E402

RULES = HERE / "rules.json"
jev = h.load_module("dayz_route_jev", HERE / "jev.py")


def load_rules(path: Path = RULES) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def match_rules(request: str, cfg: dict) -> Optional[dict]:
    """Best rule match, or None. Matches for several different routes usually mean a
    multi-step request, so the winner's confidence is cut by conflict_factor unless
    its rule absorbs the others (a whole-mod request covers its parts)."""
    hits: dict = {}  # route -> (confidence, args, absorbs), first rule in file order wins ties
    for rule in cfg["rules"]:
        for pattern in rule["patterns"]:
            m = re.search(pattern, request, re.IGNORECASE)
            if m:
                prev = hits.get(rule["route"])
                if prev is None or rule["confidence"] > prev[0]:
                    args = {k: v for k, v in m.groupdict().items() if v}
                    hits[rule["route"]] = (rule["confidence"], args, rule.get("absorbs", False))
                break
    if not hits:
        return None
    route, (confidence, args, absorbs) = max(hits.items(), key=lambda kv: kv[1][0])
    if len(hits) > 1 and not absorbs:
        confidence = round(confidence * cfg["conflict_factor"], 2)
    decision = {"route": route, "kind": cfg["targets"][route]["kind"], "confidence": confidence, "source": "rules"}
    if args:
        decision["args"] = args
    return decision


def decide(request: str, cfg: dict, env: Mapping[str, str]) -> dict:
    threshold = cfg["threshold"]
    best = match_rules(request, cfg)
    if best and best["confidence"] >= threshold:
        return best
    notes = []
    if best:
        notes.append(f"rules: best guess {best['route']} at {best['confidence']} is below {threshold}")
    else:
        notes.append("rules: no match")
    decision, jev_note = jev.route(request, cfg["targets"], env)
    if decision and decision["confidence"] >= threshold:
        return decision
    notes.append(jev_note + (f", below {threshold}" if decision else ""))
    return {"route": None, "next": "dayz-router", "note": "; ".join(notes)}


def render(decision: dict) -> str:
    if decision["route"] is None:
        return f"No confident route. Ask the dayz-router agent. ({decision['note']})"
    args = " ".join(f"{k}={v}" for k, v in decision.get("args", {}).items())
    line = f"{decision['route']} ({decision['kind']}, confidence {decision['confidence']}, from {decision['source']})"
    return f"{line} args: {args}" if args else line


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Route a DayZ request to a skill, agent or the team.")
    parser.add_argument("request", help="the user's request, quoted")
    parser.add_argument("--json", action="store_true", help="print the decision as JSON")
    ns = parser.parse_args(argv)
    if not ns.request.strip():
        parser.error("request is empty")
    decision = decide(ns.request, load_rules(), os.environ)
    print(json.dumps(decision) if ns.json else render(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
