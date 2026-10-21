# Custom `Container_Base`: non-obvious requirements

Tier 3 pack for config work on custom containers (dayz-config-specialist). Tier 2 rules in `dayz-conventions.md` still apply.

Inheriting from `Container_Base` and declaring `scope = 2; model = ...` is
not enough for the resulting object to (a) take damage, (b) stop bullets,
or (c) appear as an interactive container. Three common omissions cause
silent failures:

### 1. Declare `class Cargo`, even for a non-cargo container

Some engine builds skip container initialization entirely without it. For
containers that don't expose player cargo (loot drops via `EEKilled` etc.),
declare an empty cargo class and mark zero size:

```cpp
class MyMod_FancyContainer : Container_Base
{
    scope = 2;
    model = "\MyMod\data\fancy.p3d";

    itemsCargoSize[] = {0, 0};    // no player cargo

    class Cargo
    {
        itemsCargoSize[] = {0, 0};
        openable = 0;
        allowOwnedCargoManipulation = 0;
    };
};
```

Some builds emit an RPT warning for `itemsCargoSize[] = {0, 0}`. If yours
does, fall back to extending `Inventory_Base` and removing `class Cargo`
entirely.

### 2. `class GlobalArmor` for projectile registration

Without an armor declaration the engine may not register impacts of
projectiles, causing "bullets pass through" even when FireGeometry is
present. `GlobalArmor` sits inside `class DamageSystem`, next to
`GlobalHealth`. Its classes are keyed by damage type, the `type` an ammo's
`class DamageApplied` declares (`Bullet_762x39` declares `type="Projectile"`
in `DZ\weapons\projectiles\config.cpp:4482-4484`), not by ammo class name.
Vanilla uses `Projectile`, `Melee`, `FragGrenade` and `Infected`. Each zone
entry uses `damage = N;`, not `hit = N;`:

```cpp
class DamageSystem
{
    class GlobalHealth { /* see section 3 */ };
    class GlobalArmor
    {
        class Projectile
        {
            class Health { damage = 5; };
        };
        class FragGrenade
        {
            class Health { damage = 0; };
            class Blood  { damage = 0; };
            class Shock  { damage = 0; };
        };
    };
};
```

### 3. `healthLevels[]` (modern format, not `healthLevelValues[]`)

Modern DayZ damage system uses `healthLevels[]`. It must be nested inside
`class DamageSystem > class GlobalHealth > class Health` on the entity;
declared at root level it parses but does nothing:

```cpp
// CORRECT (modern, properly nested)
class DamageSystem
{
    class GlobalHealth
    {
        class Health
        {
            healthLevels[] =
            {
                {1.0, {"\MyMod\data\fancy.rvmat"}},
                {0.7, {"\MyMod\data\fancy_dam.rvmat"}},
                {0.5, {"\MyMod\data\fancy_dest.rvmat"}},
                {0.3, {""}},
                {0.0, {""}}
            };
        };
    };
};

// AVOID (legacy, silently breaks)
healthLevelValues[] = { 1.0, 0.7, 0.5, 0.3, 0.0 };
```

Reference: vanilla `WoodenCrate` in `DZ\gear\camping\config.cpp` lines
10157-10292 has the full pattern (`DamageSystem` with `GlobalHealth` and
`GlobalArmor`, then `class Cargo`).
