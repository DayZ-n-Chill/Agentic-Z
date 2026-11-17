# Authority publication and authenticated loopback

Audit rules for lease queues, local daemons, brokers, launchers and any control plane on localhost: when an owner or token may be made visible, and what proves which process is on the other end of a local socket. Open this in step 1 when the audited tool hands out authority or talks to a local service with a secret.

This file is about tooling around a mod (a test launcher, a local bridge to the game), not about Enforce Script, so nothing here can be checked on `P:\`. The rules come from an audit of the source author's DayZ MCP bridge and its launcher. The `CLAIM-...` ids are the source pack's claim labels, kept only for tracing.

Authentication is necessary but does not establish process provenance.

## Authority is a publication boundary

Rule `CLAIM-R21-RDA-AUTHORITY-PUBLICATION`: do not expose an owner, token or generation until the authoritative write-ahead log (WAL) transition is durably complete and re-verified.

Audit every sibling grant path, not only the canonical one. Every failure after side effects begin needs compensation plus startup recovery. Contradictory WAL or state must fence new authority and fail closed. Inject a fault at every write, flush, re-read, rename and clear boundary.

## Authenticated localhost is still a network boundary

Rule `CLAIM-R21-RDA-AUTHENTICATED-LOOPBACK`: validate both pinned host configurations and distinguish the launcher image from the native daemon image. Connect first, bind the connected socket to its exact PID, and verify executable, argv, cwd and a stable process snapshot before constructing, reading or transmitting the secret.

A healthy response, expected body, status code, port number, keyfile existence or loopback address is not process provenance.

## Productive transitive closure

Rule `CLAIM-R21-RDA-PRODUCTIVE-CLOSURE`: a secret-flow audit must cover the productive transitive closure rather than a hand-maintained file list: direct and aliased HTTP transports, request bodies, query-key construction, re-exports, closures, branches, comprehensions and nominal exceptions. Exceptions need a closed grammar and exact evidence; unresolved carriers fail closed. Include positive and negative fixtures with exact path, function, line and kind.

## Evidence

The mechanism was verified during the DayZ MCP authority and loopback audit on 2026-07-22. The tool's current lifecycle tooling separately registers an approved native launcher; that later operational state does not weaken these invariants.

The verification anchors were four files of that private project, which is not part of this repo: its MCP server module, its DayZ test tool, its native launcher transaction module and its approved-launchers list. They are named here so the rules can be traced; the files cannot be opened from this repo.
