---
name: dayz-recipe
description: "Starts a mod plan from a recipe (new weapon, new vest, new craftable): fills in the classes, the vanilla parents, the files, a task per team with a done check and the /dayz-gate behavior checks, after checking every vanilla class, script symbol and fit against P:\\. Writes output/<ModName>-plan/plan.md and behavior-checks.json for dayz-mod-architect to finish. Use at the start of a mod that is one of these common shapes."
argument-hint: "list | <weapon|vest|craftable> <ModName> [--item <Class>] [--parent <Class>] [--attachment|--magazine|--cargo|--ingredient1|--ingredient2 <Class>] [--force] [--json]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-recipe

A recipe is a plan template for a mod shape that comes up again and again. The script fills it in for your mod, checks every vanilla fact it relies on against `P:\`, and writes the draft plan. The AI only judges: `dayz-mod-architect` reads the draft, answers its open questions with the user, and writes the final plan.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\recipe.py" list
python "<skill-dir>\recipe.py" <recipe> <ModName> [options]
```

| Argument | Notes |
|---|---|
| `list` | Show each recipe, what it builds and its default vanilla classes. |
| `<recipe>` | `weapon`, `vest` or `craftable`. |
| `<ModName>` | The mod. The plan goes to `output/<ModName>-plan/` in the project cached by `/dayz-init`. The mod folder does not need to exist yet. |
| `--item` | Class name of the new item. Default `<ModName>_Rifle`, `<ModName>_Vest` or `<ModName>_Item`. |
| `--parent` and the other class options | Swap a default vanilla class. Each recipe takes only its own options (below). |
| `--force` | Replace plan files that already exist. Without it the script refuses, so a finished plan is never overwritten. |
| `--project` | Project root, when no `/dayz-init` project is cached. |
| `--out` | Write the plan somewhere else. |
| `--vanilla` | Vanilla data root. Default `P:\`. |
| `--json` | Print the full report as JSON after the verdict line. |

## The recipes

| Recipe | Builds | Options and defaults | Behavior checks |
|---|---|---|---|
| `weapon` | A firearm on a vanilla one, with new textures, the vanilla magazines and attachments, and a loot entry. | `--parent AKM`, `--attachment AK_WoodBttstck`, `--magazine Mag_AKM_30Rnd` | spawn, hands, attach |
| `vest` | A vest on a vanilla one, with new textures, the vanilla slots and cargo, and a loot entry. | `--parent SmershVest`, `--attachment SmershBag`, `--cargo Rag` | spawn, wear, attach, cargo |
| `craftable` | An item a player crafts from two vanilla items: the config class, a `RecipeBase` recipe, a modded `PluginRecipesManager` that registers it, and a loot entry. | `--parent Inventory_Base`, `--ingredient1 Rag`, `--ingredient2 DuctTape` | spawn, hands |

The templates are `recipes/<name>.json`. Each one lists the options, the fits to check, the script symbols, the classes, the files, the tasks (team, worker, done check, files, depends on), the behavior checks, what needs a person in game, and the open questions.

## What it checks on P:\

Nothing is written unless every check passes.

- Each vanilla class is defined (not just declared) in a `config.cpp` under `P:\dz\`, in the config root the recipe expects (`CfgWeapons`, `CfgVehicles` or `CfgMagazines`). The default classes are looked up in the file the recipe names first; a class you swap in is found by reading every `config.cpp`. The `CfgPatches` class of that file becomes the `requiredAddons[]` entry in the tasks.
- Each script symbol the craftable recipe relies on (`RecipeBase`, `PluginRecipesManager`, `RegisterRecipies`, the `CraftRagRope` example) is defined under `P:\scripts\`.
- Each fit holds on the vanilla config, following inheritance: the attachment's `inventorySlot` is one of the parent's `attachments[]`, the magazine is in the parent's `magazines[]`, the vest's `inventorySlot` includes `Vest`, and the cargo item's `itemSize` fits the parent's `itemsCargoSize`. A parent with no cargo (the vanilla `PlateCarrierVest` declares no `itemsCargoSize`) skips the cargo fit, and its cargo behavior check is left out.
- The parent's `hiddenSelections` are read and named in the texture tasks.

## Output and exit codes

The first line is the verdict.

| Verdict | Exit | Means |
|---|---|---|
| `WROTE` | 0 | Every check passed. One `[OK]` line per vanilla class with `path:line` and its addon, per script symbol and per fit, then the files written. |
| `FAIL` | 1 | A class is missing or a fit does not hold. One `[FAIL]` line each, saying what to pass instead: for a missed slot, the spawnable (`scope = 2`) vanilla items for each of the parent's slots; for a missed magazine, the parent's `magazines[]`. Nothing was written. |
| `ERROR` | 2 | Bad arguments, no project, no vanilla data at `P:\` (mount it with `/dayz-workdrive`), or plan files already there without `--force`. |

It writes three files to `output/<ModName>-plan/`:

- `plan.md`: the draft plan, marked as a recipe draft. Classes, the vanilla classes with `path:line`, the fits, files, the task table (Task, Team, Done check, Files, Depends on), the behavior checks, what needs a person in game, and the open questions. It notes when `workspace/<ModName>/` does not exist yet and when `workspace/<ModName>/spec.md` does.
- `behavior-checks.json`: the checks `/dayz-gate behavior` reads by default, already passed through the gate's own checker.
- `recipe.json`: the same plan as data.

## Next step

Give the draft to `dayz-mod-architect` (the orchestrator does this in its plan step). It keeps the verified classes unless the request needs others, answers the open questions with the user or the spec, and rewrites `plan.md` and `behavior-checks.json` as the final plan.

## Limits

- The config reader follows `class X: Parent` through the vanilla files only. It does not apply other mods' patches or `delete` lines, so a class changed by a loaded mod may differ in game.
- It reads unpacked `config.cpp` files. Classes that exist only in a `config.bin` are not found.
- The behavior gate cannot fire a weapon or craft an item. The plan lists those under "Needs a person in game".

## Do not

- Don't use it to change a plan the architect has finished. Ask the architect instead.
- Don't treat the draft as approved. The orchestrator still shows the task table to the user and waits for a yes.
