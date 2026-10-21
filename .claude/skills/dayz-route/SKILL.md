---
name: dayz-route
description: "Picks the skill, agent or team for a DayZ request with free keyword rules, then Jev when configured, and prints one JSON decision, including when the dayz-router agent is needed. Use when a new DayZ request arrives in the main session, before choosing a handler yourself."
argument-hint: "\"<request>\" [--json]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-route

Route a DayZ request without spending a big-model turn on it. Run it first for every new DayZ request in the main session. Skip it for follow-ups inside work that is already routed, and for non-DayZ work.

It needs no DayZ install and does not gate on `/dayz-preflight`: it only reads `rules.json` and, when keyed, calls one web API.

## How to run

```cmd
python "<skill-dir>\route.py" "<the user's request>" --json
```

Without `--json` it prints one readable line instead. It always exits 0 for a non-empty request.

## Output

One shape for every stage:

```json
{"route": "dayz-build-pbo", "kind": "skill", "confidence": 0.9, "source": "rules", "args": {"mod": "MyVest"}}
```

- `kind` `skill`: run `/<route>`, passing `args` (for `dayz-build-pbo`, `args.mod` is the mod name).
- `kind` `agent`: dispatch that agent with the user's request.
- `kind` `team` (`route` is `orchestrator`): a whole-mod build. Tell the user to start `claude --agent agentic-z:dayz-orchestrator` (or `claude --agent dayz-orchestrator` in a clone).
- `{"route": null, "next": "dayz-router", "note": "..."}`: no stage was confident. Dispatch the `dayz-router` agent with the request; it returns the same shape with `source` `router`. Follow it when `confidence` is 0.8 or more, otherwise handle the routing yourself or ask the user.

## Stages

1. **Rules** (`rules.json`, free): regex patterns per route. Matches for two different routes (for example "build MyVest and launch it") cut confidence by `conflict_factor`, because that is a multi-step request. The `orchestrator` rule absorbs other matches, since a whole-mod request names its parts. Results at or above `threshold` (0.8) are final.
2. **Jev** (`jev.py`, only with `TYPESAFE_API_KEY` set): one TypeSafe Choice question over all targets plus `other`, 5 second timeout. Missing key, network error, bad status, `other` or low confidence all fall through, with the reason in `note`. The request text is sent to `api.typesafe.ai`.
3. **dayz-router** agent: Haiku, reads nothing but the request (and `rules.json` if needed).

## Changing routes

Add a target to `targets` and a rule to `rules` in `rules.json`, and add the same target to the list in `.claude/agents/dayz-router.md`. `test_route.py` fails if a target has no skill folder or agent file, or if the two lists differ.
