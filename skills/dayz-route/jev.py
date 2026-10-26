"""Stage 2 of /dayz-route: ask TypeSafe's Jev to pick a route, only when TYPESAFE_API_KEY is set.

One Choice question over the request, with one option per route target plus `other`.
Request and response shapes follow the HTTP API at https://docs.typesafe.ai/api.md
(POST /v1/systemone; answer = {"choice", "confidence", "probabilities"}).

Never raises: a missing key, network error, timeout, non-200 status or unexpected
body returns (None, note) so the router falls through to the dayz-router agent.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Mapping, Optional, Tuple

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
TIMEOUT_S = 5
NO_MATCH = "other"
INSTRUCTIONS = (
    "This is a request from a DayZ modder to their coding assistant. "
    "Which single handler should take it? Pick `other` when it needs several handlers, "
    "is not about DayZ modding, or is too vague to tell."
)


def build_payload(request: str, targets: Mapping[str, dict]) -> dict:
    criteria = {name: t["description"] for name, t in targets.items()}
    criteria[NO_MATCH] = "None of the above fits, or the request needs several of them"
    return {
        "model": MODEL,
        "state": {"request": request},
        "questions": {"route": {"type": "choice", "instructions": INSTRUCTIONS, "criteria": criteria}},
    }


def route(request: str, targets: Mapping[str, dict], env: Mapping[str, str]) -> Tuple[Optional[dict], str]:
    """Return (decision, note). decision is None when Jev was skipped, failed, or chose `other`."""
    key = env.get("TYPESAFE_API_KEY", "").strip()
    if not key:
        return None, "jev: skipped (TYPESAFE_API_KEY not set)"
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(build_payload(request, targets)).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            answer = json.loads(resp.read().decode("utf-8"))["answers"]["route"]
        choice = answer["choice"]
        confidence = float(answer["confidence"])
    except Exception as exc:  # any service failure falls through to the model stage
        return None, f"jev: failed ({type(exc).__name__}: {exc})"
    if choice == NO_MATCH:
        return None, f"jev: no single handler fits (confidence {confidence:.2f})"
    if choice not in targets:
        return None, f"jev: returned unknown route {choice!r}"
    decision = {"route": choice, "kind": targets[choice]["kind"], "confidence": round(confidence, 2), "source": "jev"}
    return decision, f"jev: {choice} at {confidence:.2f}"
