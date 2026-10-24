# DayZ config conventions (Tier 2 topic)

Part of Tier 2. Config conventions, the `inventorySlot` string-versus-array bug, and bundle / umbrella mods. Read it together with the core rules in `.claude/skills/_shared/dayz-conventions.md`, which still apply.

## Config conventions

- `config.cpp` is the canonical declaration entry point.
- Use `hiddenSelections` + `hiddenSelectionsTextures` for retextures rather than duplicating models.
- Inherit from vanilla classes (requires vanilla data on `P:\`).
- Custom containers: see `.claude/skills/_shared/container-base.md` (the `class Cargo`, `GlobalArmor` and `healthLevels[]` requirements).

## `inventorySlot`: string vs array (`T148506`)

Vanilla declares `inventorySlot` in two forms: a string for a single slot, and an array for several.

```cpp
// String form (DZ\vehicles\parts\config.cpp:822-831):
class GlowPlug : Inventory_Base
{
    inventorySlot = "GlowPlug";
};

// Array form (DZ\gear\camping\config.cpp:10157-10173):
class WoodenCrate : Container_Base
{
    inventorySlot[] = {"Truck_01_WoodenCrate1", "Truck_01_WoodenCrate2", "Truck_01_WoodenCrate3", "Truck_01_WoodenCrate4"};
};
```

Appending with `inventorySlot[] += {...}` to a class whose parent uses the string form fails silently: the mod's slot is dropped at parse time, and the slot just refuses the item with no RPT or script error (Bohemia tracker `T148506`). So whenever a mod class changes a parent's `inventorySlot`, redeclare the whole array with `=` and keep the parent's existing entries:

```cpp
class MyMod_GlowPlug : GlowPlug
{
    inventorySlot[] = {"GlowPlug", "MyMod_CustomSlot"};   // not += {"MyMod_CustomSlot"}
};
```

Check the parent's declaration on `P:\` first (Grep for the class name) so the copied entries match what vanilla ships.

## Bundle / umbrella mods (pre-compiled PBOs)

Not every `workspace/<ModName>/` is buildable source. A bundle carries pre-compiled artifacts: third-party or purchased mods distributed as PBO-only, or an umbrella `@mod` collecting many pre-built PBOs under one container.

- `workspace/<ModName>/Addons/*.pbo` (+ matching `*.bisign` signatures): the pre-compiled payload.
- `workspace/<ModName>/Keys/*.bikey`: public keys; deploy to `P:\Mods\@<ModName>\Keys\`.
- Optional `meta.cpp` / `mod.cpp` at the bundle root.
- Optional linker `config.cpp` + `$PBOPREFIX$`: a content-free `CfgPatches` declaring `requiredAddons[]`, built from source like any mod.

Build and deploy are separate paths with separate gates. The `config.cpp` + `$PBOPREFIX$` requirement (and the `P:\<ModName>\` junction) applies to the build path only (`/dayz-build-pbo`, which runs AddonBuilder). The deploy path (`/dayz-deploy-pbo`) is an idempotent copy of the pre-compiled payload into `P:\Mods\@<ModName>\` and requires none of them. Both paths write the same `.agentic-z-scaffold` ownership marker; `/dayz-deploy-pbo` and `/dayz-clean-workspace` refuse to touch an existing `@<ModName>` dir that lacks it (it could be a subscribed or hand-placed mod).

Umbrella pattern: each payload PBO keeps its own prefix (baked in when it was compiled); `@<ModName>` is just the container. Never merge several mods into one re-prefixed PBO: that needs a destructive config and asset merge and breaks external `requiredAddons[]` references. A full umbrella is the built linker PBO (via `/dayz-build-pbo`) plus the copied payload (via `/dayz-deploy-pbo`) side by side under one `@<ModName>\Addons\`; deploy never deletes, so order does not matter.
