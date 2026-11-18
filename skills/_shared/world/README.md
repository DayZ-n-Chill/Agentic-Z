# World pack

Tier 3 reference for what a DayZ world does beyond its terrain: holes in the terrain, underground areas and the player's underground state, the 1.30 hazards (sandstorm, heat stroke, dust agents, surface dust, oil pits), the Badlands world, and the layout of the `.wrp` world file. Written for `dayz-map-specialist`; any DayZ worker may load one file of it when a task needs it. Tier 1 and Tier 2 still apply on top.

Every game fact here cites the vanilla file on `P:\` it came from, read on DayZ 1.30. Line numbers match the vanilla data at the time of writing; if a line has moved, Grep the class or key name in the same file. Nothing in this pack has been tested in a running game. A line marked "not on `P:\`" comes from the game's own PBOs, executable or release notes, and a line marked "later 1.30 update" describes a newer build than the data on `P:\`; neither is checked there.

Who writes what: the map specialist owns the world config (`CfgWorlds`, including `Holes`); mission files (`cfgundergroundtriggers.json`, `cfgeffectarea.json`, `cfggameplay.json`, `cfgbunkerbroadcast.json`) go to dayz-server-admin; script classes (world data, modifiers, agents, trigger spawning, effect areas) go to dayz-script-specialist; protective gear items go to dayz-config-specialist with the wearables pack.

## Which file to open

| Question | File |
|---|---|
| How do I open a hole in the terrain, which unit do `tiles[]` use, how does Terrain Builder mark holes, and what is still unproven? | `terrain-holes.md` |
| Where are holes stored, why is a Livonia cell 6.25 m, which engine strings load holes, and how do I check a new game build? | `terrain-holes-storage.md` |
| What are the fields of `cfgundergroundtriggers.json`, how is it loaded and synced, how do I tie a trigger to my bunker, how does the trigger editor work? | `underground-triggers.md` |
| What is the player's underground state, who decides it, and which items are refused underground? | `underground-presence.md` |
| What does Badlands add: Nasdara world data, bunkers announced by radio, the irrigation tunnel, its data files? | `nasdara-badlands.md` |
| How is a `.wrp` world file laid out, how is a road graph pulled out of one, and what is a map's real world name? | `wrp-format-and-road-graph.md` |
| How do I start or balance a sandstorm on my map, what counts as shelter, what do infected hear in one? | `sandstorm.md` |
| How does heat stroke build, what cools a player, how do shade, sun and vehicle wind work? | `heat-stroke.md` |
| Which mask or glasses stop silicosis and eye irritation, and what do the agents do? | `dust-agents-and-protection.md` |
| Where do ceiling, ambient, kickup and vehicle dust come from? | `surface-dust.md` |
| How does an oil pit work, how do I place one, how do I write my own effect area? | `oil-pits.md` |
| Which vanilla file holds which hazard, what can't `P:\` show, and which facts are easy to get wrong? | `hazards-vanilla-file-map.md` |

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| A motorbike rider keeps squinting and collecting silicosis in a storm | Only a `Car` shelters; a motorbike or boat does not | `sandstorm.md` |
| Standing under an eave or a crashed helicopter doesn't stop the storm | Shelter needs a roof and the building sound environment; wrecks and trees are excluded | `sandstorm.md` |
| A 1.29 mod that trims heat damage does nothing; players still die of heat | Deadly heat moved from `HeatComfortMdfr` to heat stroke phase 4 | `heat-stroke.md` |
| The sickness icon doesn't come back, or stays on | Heat stroke phases 1 and 2 don't balance the disease count | `heat-stroke.md` |
| Glasses don't stop silicosis, or a mask doesn't stop squinting | Breathing and eye protection are separate values | `dust-agents-and-protection.md` |
| A custom effect area never resizes its particles or never iterates | It overrides `OnCEUpdate`; 1.30 ticks `OnCEIterate` | `oil-pits.md` |
| Wheel or step dust ignores a custom surface, or warns as obsolete | The old `Surface` getters and `EffWheelSmoke.SetSurface` are obsolete | `surface-dust.md` |
| A freshly placed oil pit does no damage | It burns only after a 3 to 9 s delay | `oil-pits.md` |
| Shade doesn't register for many seconds | The shade check runs every 30 s, not every 5 s | `heat-stroke.md` |
| Changing the script weather noise helpers doesn't change what infected hear | AI noise dampening is native and reads `AIParams` | `sandstorm.md` |
| No sunstroke on a custom map | The world data doesn't fill the sun table | `heat-stroke.md` |
| A bunker isn't dark inside | No underground trigger covers it; a hole alone doesn't darken | `underground-triggers.md` |

## Setting up a custom world

1. Holes, if the world opens to an underground space: `terrain-holes.md`, then the geometry under them in the `.wrp`.
2. Underground triggers for each dark space: `underground-triggers.md`.
3. Storms: the world's `class Sandstorm`, `sandstormFrequency` and a `Start` call from the mission or the world data: `sandstorm.md`.
4. Heat and sun: the world data's sun table and the thermal bias constants: `heat-stroke.md`.
5. Dust: the surfaces' dust entries and the world data's dust settings: `surface-dust.md`.
6. Oil pits and other areas through the mission's `cfgeffectarea.json`: `oil-pits.md`.
7. Protective gear for the new hazards: `dust-agents-and-protection.md`.
8. Check offline with `/dayz-lint` (its second stage, the script validator under `scripts/tools/dayz-script-validator/`, checks the Enforce Script), then in game with `/dayz-launch-test`; each hazard and hole file says what to look for. Build and ship with `/dayz-build-pbo` and `/dayz-gate`.

## Related packs

| Topic | Go to |
|---|---|
| Base building parts, rebuilding, code locks | `_shared/persistence/base-building.md` |
| The state file of the bunker broadcast | `_shared/persistence/versioning-and-migration.md` |
| The player save stream the thermal bias handler writes into | `_shared/persistence/save-load-contract.md` |
| Trigger volumes in general (`ScriptedEntity`, `TriggerEvents`) | `_shared/physics/scripted-triggers.md` |
| Water queries over rivers and ponds | `_shared/physics/water-queries.md` |
| What infected hear (`AIParams`), animal territories | `_shared/ai/perception.md`, `_shared/ai/animal-territories.md` |
| The mask or glasses item, its model and slots | `_shared/wearables/references/protection-and-insulation.md` |
| Vehicle classes and their effect components | `_shared/vehicles/` |
| `.ptc` and `.emat` files, particle IDs, playing particles | `/dayz-particles` and `dayz-particles/references/dayz-1-30-particles.md` |
| Contaminated area particle budget | `dayz-particles/references/effect-area-particles.md` |
| Proton and Linux limits | `_shared/linux-proton.md` |
