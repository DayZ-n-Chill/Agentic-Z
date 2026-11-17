# Knowledge notes pack

Tier 3 reference: cross-cutting DayZ notes that fit no single topic pack. Each file is one topic: a source map of a vanilla system, a set of measured results, a field note from mod projects, or an index of outside sources. Any DayZ worker may load one file of it when a task needs it. Tier 1 and Tier 2 still apply on top, and where a note here and a Tier 2 file state the same rule, Tier 2 wins.

How far to trust a file is in its `Status:` line, directly under the title:

- **Checked on `P:\`** means every cited vanilla line was opened and holds what the note says.
- **Not yet checked on `P:\`** means vendored content: measured results, tool behaviour or third-party facts. Treat those facts as leads, not answers. Each such file still lists the few lines that were checked.
- Third-party facts name the mod, tool or page they come from (Community Framework, Expansion, VPP AdminTools, LBmaster, DayZ-MCP, the StarDZ and DZconfig wikis, the Bohemia wiki).
- `[EXACT][CLAIM-...]` tags are claim IDs of the source pack's claim registry, `scripts/dev/knowledge-pack/sources/claims.json`.
- Several notes cite build `119356`. The `P:\scripts` tree was compared with it on 2026-11-17: the cited lines match, but the `proto native` counts and the Workbench API files differ, so it is not the same tree (see `vanilla-native-surface.md` and `workbench-scripting-api.md`).

## Which file to open

| Question | File | Checked on `P:\` |
|---|---|---|
| In what order do `MissionServer` and `MissionGameplay` run their constructor, `OnInit`, `OnMissionStart` and `OnUpdate`, and where does `super` go | `mission-lifecycle.md` | Yes |
| How does a player's own input travel to the server (`ScriptInputUserData`), and when is that the right channel instead of `ScriptRPC` | `script-input-user-data.md` | Yes |
| How long a string fits in a `ScriptRPC` or a `ScriptInputUserData` packet, how deep the input queue is, whether RPC order is kept, what an ACK proves | `script-network-limits.md` | Measured, not yet checked |
| Does an `array<int>` survive `ScriptRPC` (to 256) and `ScriptInputUserData` (to 37) | `script-network-arrays.md` | Measured, not yet checked |
| Larger `array<int>`, `array<string>` and nested arrays over both channels, and why `array<array<int>>` loses its rows | `script-network-array-types.md` | Measured, not yet checked |
| How many `proto native` declarations exist and where; what `owned` and `static` mean on one; how to call `GetBoneMatrix` or `AudioSystem.BankLoad` | `vanilla-native-surface.md` | Yes (counts differ, see its status) |
| What `GenericComponent`, `ScriptComponent` and `GenericEntity` declare, their event order, and the `COMPONENT_SYSTEM` guard | `entity-component-system.md` | Yes |
| Which Enforce Script entry points, modules, plugins and events extend Workbench itself | `workbench-scripting-api.md` | No (`P:\` holds an older API; see its last section) |
| What the DayZ-MCP bridge exposes, the design rules that keep it safe, and the engine facts it had to discover (seat versus ownership, `SetThrottle`, freecam) | `mcp-bridge-protocol.md` | Engine facts yes; the tool no |
| Running DayZ Tools, the server, the client and DayZ-MCP on Linux under Proton and podman: what was measured, what failed, what was corrected | `linux-proton-findings.md` | Measured, not yet checked |
| Work drive and mod layout, diag binaries, `allowFilePatching`, AddonBuilder and CfgConvert gotchas, launch commands, mission files, BattlEye kick codes, which log holds what | `environment-and-infra.md` | Vendored; cited lines checked |
| py3d fields, LOD resolutions, winding when porting from Blender, debris offsets, double-sided faces, `ThrowPhysically`, `ServerSetAmmoCount`, JSON schema migration, LBmaster presets, a loot cascade | `technical-notes.md` | Cited lines checked; measurements vendored |
| Has this been tried and ruled out already: screen capture from a mod, `CallExtension`, runtime textures, debris physics, the two animation systems, and a list of config and script gotchas | `verified-capabilities.md` | Vendored; its last section lists what was checked |
| The seven invariants every vehicle hits (get-in, script binding, `class=vehicle`, `componentNN`, proxies, wheel axis, vital plug) and which project earned each | `vehicles-crossproject.md` | Rows 1 and 7 yes; the rest measured |
| Wiki-sourced configuration: contaminated areas, weather, underground, stamina and temperature keys, surfaces, server launch parameters, diag menu, object and gear spawners, the tools EULA | `wiki-systems-reference.md` | No; its last section lists what was checked |
| Community-sourced facts on script layers and load order, language gotchas, `types.xml` fields and flags, events, loot balancing | `stardz-dzconfig-distill.md` | No; its last section lists what was checked |
| Which public sources were harvested (wiki hubs, GitHub READMEs, API explorers) and where the pointers are | `public-wiki-harvest.md` | No (an index of pointers) |
| Which DayZ build a fact or a line number belongs to, what 1.30 changed from 1.29, and what each 1.30 build (164200, 164289) changed; use it when porting a 1.29 mod or when a citation lands on the wrong line | `dayz-1-30-build-history.md` | The older-build side yes; the 1.30.164200 and 1.30.164289 side not yet (`P:\` holds an older 1.30 build) |
| Is this belief one the Knowledge Pack once taught and later corrected (script and engine API, winding and collision, UI, animation, testing and building), and what replaced it | `retracted-claims-ledger.md` | Cited lines yes; measured corrections not yet checked |
| The script tree is not strict UTF-8, which macros DayZDiag defines, how a run of `>` closes a nested template, why a cast between unrelated classes stops the module, how big the script tree is by build | `engine-findings-from-pack-history.md` | Cited lines yes; counts and measurements not yet checked |
| The process rules for DayZ work with an agent: the four rules (never invent an API, client/server split, in-game tests are expensive, honest verification), evidence rules, the six verification levels, what to do when the game updates | `working-rules.md` | Cited lines yes; the rest is process, not game facts |
| One pass through making a mod (understand, write, lint, pack, deploy, test, debug), what must be installed, and the route from "I want X" to the skill or tool | `mod-cycle.md` | Cited lines yes; tool behaviour not yet checked |

## Related packs

- Enforce Script API by topic, with every line checked: `_shared/enscript/references/` (networking is `api_network.md`).
- Persistence stream contract: `_shared/persistence/`.
- Vehicles in depth: `_shared/vehicles/`.
- LOD resolutions and asset rules: `_shared/conventions/assets.md`. Custom containers: `_shared/container-base.md`. Physics of spawned items: `_shared/enscript/patterns/physics_items.md`.
- Test server layout of this repo: `_shared/conventions/server.md`.

## Related docs and tooling

- What each tool under `scripts/tools/` does, with a by-symptom table: `docs/knowledge-pack-tools.md`.
- Which DayZ build each imported skill was checked on, and how: `docs/compatibility-matrix.md`.
- The optional in-game bridge (install and wiring): `docs/dayz-mcp.md`.
- The claim registry and the `packctl` gate the `[EXACT][CLAIM-...]` tags refer to: `scripts/dev/knowledge-pack/`, described in `docs/knowledge-pack-maintenance.md`.
