# Pre-implementation grill: the DayZ questions to settle first

The questions to go through with the user before writing the `config.cpp`, `model.cfg` or scripts of a placeable or usable DayZ object. `dayz-mod-workflow` runs it in its activation check. It is opt-out, not opt-in: a generic "any questions?" pass does not reach the DayZ-specific axes, and skipping this list brings back silent assumptions.

In this repo no agent or skill asks these for you: `dayz-mod-architect` does not cover them and can only return open questions, and `/dayz-recipe` drafts a plan from a one-line request without them. The main session settles them with the user, before or alongside planning, and the answers go into `output/<ModName>-plan/plan.md`.

## How to ask (non-technical users)

For each axis, offer **closed options with a recommended default** (AskUserQuestion where the agent has it), not open questions. If the user does not understand a question, explain it with a concrete vanilla example; do not fill in a silent default. When an answer changes the questions that follow, ask **one at a time**.

## Axes to cover (the minimum for any placeable or usable object)

1. **Crafting, if any.** Exact quantities, the required tool (yes or no, and which), animation time, sound. A reasonable default: 2 to 6 units of the main material, no tool, 1 to 3 s.
2. **Carried in hands.** Weight in grams, `itemSize` in slots (warn when the size makes it "hands only"), carry pose (default or specific).
3. **Deploy and placement.** Hologram sounds, valid surfaces (terrain, interior, water), starting orientation, level snap or follow the slope, rotation while the hologram shows.
4. **Placed state.** **Pickup yes or no, and how.** This one is critical and very easily left unsaid: not adding a take action does not mean the engine has none by default. To block pickup, choose one of the two recipes in `error-catalog.md`, "E12: stopping pickup", and refuse `CanPutInCargo()` and `CanPutIntoHands()`. Damage: hit points, sources (bullets, melee, weather), behaviour at 0 health (ruined or destroyed), drops on destruction. `carveNavmesh`. Persistence and lifetime.
5. **Internal cargo.** Does it store items? If it can be worn: which attachment slots it exposes (a subset or all).
6. **Visual and UX.** Inventory icon (a `.paa`: generate it or wait for the user's), `displayName` and `descriptionShort` (language, tone, a stringtable with `#STR_<PREFIX>_*` keys).
7. **Spawn and distribution.** Crafting only, loot, trader, admin, or a mix. TraderPlus or Expansion Market compatibility if it applies (third-party mods).
8. **Umbrella mod, if it is one.** The policy: one PBO for all future objects, or sub-mods. The class naming convention (`<PREFIX>_<Object>`). Bundles in this repo: `skills/_shared/conventions/config.md`, "Bundle / umbrella mods".
9. **Compatibility with third-party mods.** Expansion, CF, Dabs, TraderPlus, territory mods (BaseBuildingPlus, Expansion Territory). Ask what the server runs. `/dayz-conflict-check` reports collisions with CF, COT and Expansion.
10. **Advanced phases, if any.** For wearable characters, vehicles or complex crafting: list the axes of that phase (slots, cargo in garments, decay, limits).

## The mistake to avoid

"The user chose X, so by implication they also want Y and Z." No. Each decision is confirmed. If an option's label bundles several features ("is placed, has health, can be picked up"), treat each feature as a separate confirmation before implementing it. Measured on a mannequin mod: the label "deployable base-building" included "can be picked up", and the user had to cut it out by hand during implementation.

A real case with a default and a question per point makes a good template for the next one; keep yours with the plan.

## Related rules

Ask before assuming; do not add what was not asked for, and by extension do not assume what was not asked for; write criteria that can be verified (`/dayz-scope-mod`, `references/spec-checklist.md`). Tier 1 says the same under "Scope".
