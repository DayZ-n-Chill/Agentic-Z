# Questions before building an object

Which questions to settle with the user before writing the `config.cpp`, `model.cfg` or scripts of a placeable or usable DayZ object, and how to ask them. The implementation protocol (`implementation-protocol.md`) checks for the answers before any code. Go through the list unless the user says to skip it: a general "any questions?" never reaches the DayZ-specific points, and skipping them brings back silent assumptions.

No agent or skill asks these for you. `dayz-mod-architect` does not cover them and can only return open questions, and `/dayz-recipe` drafts a plan from a one-line request without them. The main session settles them with the user, before or alongside planning, and the answers go into `output/<ModName>-plan/plan.md`.

## How to ask

Users are often not technical. For each point, offer closed options with a recommended default (AskUserQuestion where the agent has it), not open questions. If the user does not understand a question, explain it with a concrete vanilla example; never fill in a silent default. When one answer changes the questions that follow, ask one at a time.

## What to cover for any placeable or usable object

1. **Crafting, if any.** Exact quantities, the tool needed (whether one is, and which), animation time, sound. A reasonable default: 2 to 6 units of the main material, no tool, 1 to 3 s.
2. **Carried in hands.** Weight in grams, `itemSize` in slots (warn when the size makes it hands only), carry pose (default or a specific one).
3. **Deploying and placing.** Hologram sounds, valid surfaces (terrain, interior, water), starting orientation, level or following the slope, rotation while the hologram shows.
4. **Once placed.** Whether it can be picked up, and how. This one is easily left unsaid, and leaving out a take action does not mean the engine has none by default. To block pickup, use one of the two recipes in `skills/dayz-launch-test/references/error-catalog.md`, "Stopping pickup (E12)", and refuse `CanPutInCargo()` and `CanPutIntoHands()`. Damage: hit points, sources (bullets, melee, weather), what happens at 0 health (ruined or destroyed), what drops when it is destroyed. `carveNavmesh`. Persistence and lifetime.
5. **Cargo inside.** Does it store items? If it can be worn: which attachment slots it offers, some or all.
6. **Look and text.** Inventory icon (a `.paa`: generate it or wait for the user's), `displayName` and `descriptionShort` (language, tone, a stringtable with `#STR_<PREFIX>_*` keys).
7. **Spawning and distribution.** Crafting only, loot, trader, admin, or a mix. TraderPlus or Expansion Market compatibility if it applies (third-party mods).
8. **An umbrella mod, if it is one.** One PBO for all future objects, or sub-mods; the class naming convention (`<PREFIX>_<Object>`). Bundles in this repo: `skills/_shared/conventions/config.md`, "Bundle / umbrella mods".
9. **Third-party mods.** Expansion, Community Framework, Dabs Framework, TraderPlus, territory mods (BaseBuildingPlus, Expansion Territory). Ask what the server runs. `/dayz-conflict-check` reports collisions with Community Framework, COT and Expansion.
10. **Later phases, if any.** For wearable characters, vehicles or complex crafting, list the points of that phase (slots, cargo in garments, decay, limits).

## The mistake to avoid

"The user chose X, so they also want Y and Z." Confirm each decision on its own. If an option's label bundles several features ("is placed, has health, can be picked up"), confirm each feature separately before implementing it. On a mannequin mod the label "deployable base building" included "can be picked up", and the user had to cut that out by hand during implementation.

A real case with a default and a question per point makes a good template for the next one; keep yours with the plan.

Ask before assuming; do not add what was not asked for, and so do not assume it either; write criteria that can be checked (`spec-review.md`). Tier 1 says the same under "Scope".
