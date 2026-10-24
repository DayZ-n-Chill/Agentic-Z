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


class RulesError(Exception):
    """rules.json is missing, is not valid JSON, or holds a bad rule."""


def load_rules(path: Path = RULES) -> dict:
    """Read and check rules.json. Raises RulesError with a one-line reason naming the file."""
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RulesError(f"{path.name}: cannot read ({exc.strerror or exc})") from exc
    except json.JSONDecodeError as exc:
        raise RulesError(f"{path.name}: not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg})") from exc
    try:
        targets = cfg["targets"]
        for key in ("threshold", "conflict_factor"):
            float(cfg[key])
        for i, rule in enumerate(cfg["rules"], 1):
            where = f"{path.name}: rule {i} ({rule.get('route')!r})"
            if rule["route"] not in targets:
                raise RulesError(f"{where}: route is not in targets")
            absorbs = rule.get("absorbs", False)
            if not (isinstance(absorbs, bool) or absorbs == "all"
                    or (isinstance(absorbs, list) and all(r in targets for r in absorbs))):
                raise RulesError(f"{where}: absorbs must be true, false, \"all\" or a list of target names")
            for pattern in rule["patterns"]:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise RulesError(f"{where}: bad regex {pattern!r} ({exc})") from exc
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RulesError(f"{path.name}: missing or malformed field ({type(exc).__name__}: {exc})") from exc
    return cfg


def _absorbed(other: str, absorbs, same_words: bool, targets: Mapping[str, dict]) -> bool:
    """Whether a winning rule with this absorbs value covers a match for route `other`.
    true covers routes that are not separate steps (an item specialist, a named object),
    and a step only when its match overlaps the winner's (the same words read two ways,
    such as "rebuild" in "rebuild the search index"); a list also covers the steps it
    names, because they are part of the winner's own work; "all" (pasted content, the
    whole-mod team) covers everything."""
    if absorbs == "all":
        return True
    if not absorbs:
        return False
    if not targets[other].get("step", False) or same_words:
        return True
    return isinstance(absorbs, list) and other in absorbs


def match_rules(request: str, cfg: dict) -> Optional[dict]:
    """Best rule match, or None. Matches for several different routes usually mean a
    multi-step request, so the winner's confidence is cut by conflict_factor unless
    its rule absorbs every other match (see _absorbed). A separate step such as a
    build, lint or types.xml edit is never absorbed by a rule whose work does not
    include it. A rule's fixed "args" (such as the triage mode) join the args its
    pattern captures."""
    hits: dict = {}  # route -> (confidence, args, absorbs, span), first rule in file order wins ties
    for rule in cfg["rules"]:
        for pattern in rule["patterns"]:
            m = re.search(pattern, request, re.IGNORECASE)
            if m:
                prev = hits.get(rule["route"])
                if prev is None or rule["confidence"] > prev[0]:
                    args = {**rule.get("args", {}), **{k: v for k, v in m.groupdict().items() if v}}
                    hits[rule["route"]] = (rule["confidence"], args, rule.get("absorbs", False), m.span())
                break
    if not hits:
        return None
    route, (confidence, args, absorbs, (start, end)) = max(hits.items(), key=lambda kv: kv[1][0])
    for other, (_, _, _, (o_start, o_end)) in hits.items():
        same_words = o_start < end and start < o_end
        if other != route and not _absorbed(other, absorbs, same_words, cfg["targets"]):
            confidence = round(confidence * cfg["conflict_factor"], 2)
            break
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
    try:
        cfg = load_rules(RULES)
    except RulesError as exc:
        print(f"dayz-route: {exc}", file=sys.stderr)
        return 1
    decision = decide(ns.request, cfg, os.environ)
    print(json.dumps(decision) if ns.json else render(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
