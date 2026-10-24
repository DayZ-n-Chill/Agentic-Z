# Registering a new agent

`agent-creator` (`.claude/agents/agent-creator.md`) follows this list after it writes a new file to `.claude/agents/<name>.md`. Change one file per line, and skip lines that don't fit the role. The test named in brackets fails when a line is missed; run all of them with `py -m pytest -q scripts/dev/`.

- `.claude-plugin/plugin.json`: add the agent to the `"agents"` list (`test_every_agent_is_registered_in_the_plugin`).
- `.claude/agents/dayz-lead.md`, for a new dayz-* worker: add it to the Team table under "## Your workers" (`test_every_dayz_worker_is_in_the_lead_table`).
- `.claude/agents/dayz-lead.md` and `.claude/agents/dayz-orchestrator.md`, for a worker whose report holds work for another team: write that work under a "For the <team> lead" heading, and make sure both files already forward that heading, as they do for "For the server lead". Add the heading to both if it is new, or the work is dropped (`test_lead_and_orchestrator_forward_every_worker_heading` in `scripts/dev/test_cross_team_headings.py`).
- `docs/dayz-modding.md`: add a row to the "Superpowers ↔ DayZ specialist routing" table for every lead worker and gate (`test_every_lead_worker_and_gate_is_in_the_docs_routing_table`).
- `.claude/skills/dayz-route/rules.json`: add a lead worker or gate that a request can start directly to `"targets"` (`"kind": "agent"` and a one-line description), plus a rule with patterns when a request names its work clearly, so `/dayz-route` can send work to it (`test_every_lead_worker_is_a_route_target`). Skip a stage reached only through another agent, like `figma-to-dayz-layout`.
- `.claude/agents/dayz-router.md`: add the same name under "## Valid routes" as `` - `<name>` (agent): `` and what it handles (`test_router_agent_lists_exactly_the_targets` keeps this list equal to the `rules.json` targets).
- `.claude/agents/dayz-mod-debugger.md`: for a worker that edits mod files, name it under "## Who fixes what" with the files or classes it owns, so the debugger names it as the Owner of a fix (`test_every_file_owning_worker_is_a_debugger_owner`).
- `.claude/skills/_shared/dayz-conventions.md`: add its short name (without `dayz-`) to the "Read by" column of the topic table for every `conventions/*.md` file it reads.
- `scripts/dev/test_repo_integrity.py`: add a gate (reports and never edits) to `READ_ONLY_GATES` instead of the lead table; a planner, router or lead to `NOT_LEAD_WORKERS`; a role that writes nothing itself (it only runs other agents, like `dayz-lead`, or only diagnoses, like `dayz-physics-specialist`) to `NO_WRITE_ROLES`.
- `evals/questions/<name>.json`: write it in the format given in `docs/evals.md`, with at least one `must_include`/`must_not_include` question, and put any fixtures it reads under `evals/fixtures/<name>/`.
- `evals/baseline.json`: run `py scripts/dev/run_evals.py --agent <name> --update-baseline` to record its score. Never edit that file by hand; the runner refuses to lower a score.
- `evals/README.md`: remove the agent from the "Not yet covered" names in the first paragraph, and raise the covered count there.
