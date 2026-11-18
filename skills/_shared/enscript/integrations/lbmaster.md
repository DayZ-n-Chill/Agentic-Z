# LBmaster loot presets

How a mod spawns LBmaster loot presets without needing LBmaster loaded, which of the two spawn calls respects a preset's own chance, and the order to try loot sources in when LBmaster is only one of them.

LBmaster is a third-party mod pack, not part of the game. Every fact below is checked against its own scripts in `LBmaster_Core.pbo`, which ship as plain text; the paths are paths inside that PBO. Recheck them after an LBmaster update.

## Keeping LBmaster optional

Leave LBmaster out of `requiredAddons[]` and wrap every line that names an LBmaster class in a preprocessor guard. The mod then builds and runs on a server without LBmaster, and uses presets when LBmaster is there.

The guard must be a name that LBmaster's `CfgMods` lists in `defines[]`. `LBmaster_Core.pbo` declares `LBmaster_Rework` and `LBmaster_QrCode` (its `config.cpp`). The PBO name `LBmaster_Core` is not a define, so `#ifdef LBmaster_Core` compiles the guarded code out even with LBmaster loaded. Read the `defines[]` of the LBmaster version the server runs before you pick the name.

```c
#ifdef LBmaster_Rework
	if (LB_PresetLoader.Get)
	{
		LB_PresetBase preset = LB_PresetLoader.Get.GetPreset("Crate_Tools");
		if (preset)
			preset.SpawnPreset(player, this);
	}
#endif
```

## The calls

| Call | Where | Notes |
|---|---|---|
| `LB_PresetLoader.Get` | `scripts\3_Game\LBmaster_Core\Config\Loader\LBConfigLoader.c:5` | A static field, not a method: write `Get.GetPreset(...)`, never `Get().GetPreset(...)`. It is set when the config loads (`:158`) and set back to `null` by `Delete` (`:179`), so test it before use |
| `GetPreset(string name)` | `scripts\4_World\LBmaster_Core\Config\LB_PresetLoader.c:146` | `null` when no preset has that name |
| `FindPresets(TStringArray names)` | `LB_PresetLoader.c:189` | Skips names that don't resolve; returns an empty array, never `null`, when none do |
| `SpawnPreset(player, parent, altPos, radius)` | `scripts\4_World\LBmaster_Core\Struct\LB_PresetBase.c:138` | Instance call on one preset |
| `static SpawnPresets(player, presets, parent, altPos, radius)` | `LB_PresetBase.c:92` | Static call on a list of presets |

## Which call respects the chance

The two calls treat a preset's own `chance` differently.

- `SpawnPreset` ignores it. It goes straight into the `minSpawnTries` to `maxSpawnTries` loop (`LB_PresetBase.c:139` to `:148`), so the preset always spawns. Chance applies only to its children: the linked presets are rolled inside the loop (`:169` onwards).
- `SpawnPresets` applies it. Presets with `individualChance = false` share one weighted roll, and exactly one of them spawns (`:100` to `:124`). Presets with `individualChance = true` each roll their `chance` alone (`:125` to `:134`; `ChechIndividualChance` at `:71`, LBmaster's spelling). A list whose presets all use individual chances below 1.0 can spawn nothing.

Use `SpawnPreset` when the loot must appear, such as a crate that has just broken open. Use `SpawnPresets` when the preset's chances are meant to decide.

## Trying loot sources in order

A mod that can take loot from LBmaster, from its own table and from a plain class list tries them from the richest to the simplest and falls through when one gives nothing:

1. LBmaster presets, only when the admin has switched them on. If LBmaster isn't loaded or the preset name doesn't resolve, log a warning and fall through.
2. The mod's own loot table, with its nested attachments. An empty table falls through quietly.
3. The plain list of class names.
4. Nothing left: log one line saying no loot source is configured, so the admin sees an empty config instead of a silent crate.

An admin can then switch sources by editing the config, an old config keeps working when a source is added, and a server without LBmaster still gets loot from step 2 or 3. This order is a design choice for your mod, not LBmaster behaviour.
