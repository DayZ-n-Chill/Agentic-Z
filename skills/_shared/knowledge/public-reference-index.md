# Public DayZ reference outside the repo: where to look and how far to trust it

Covers which public reference exists for DayZ modding outside this repo (the Bohemia Interactive wiki pages by topic, Bohemia's GitHub repositories, community wikis and script browsers), what each answers, and how far each can be trusted.

Status: an index of pointers. Not yet checked on `P:\`: it states almost no game facts. The one it repeats was checked on 2026-11-17: `P:\scripts` holds no `CfgStamina` class, and the stamina maximum is the constant `STAMINA_MAX` at `P:\scripts\3_game\constants.c:749`.

This file holds pointers only. The game facts themselves are in `wiki-systems-reference.md` (contaminated areas, stamina and `cfggameplay.json`, diag menu categories, object and gear spawners, surfaces). Open that note for a fact, and this one to find the page that covers a topic.

## Trust order

1. The vanilla files on `P:\` (`P:\scripts`, `P:\DZ`) and the mission files shipped with the server. They answer for the build they were extracted from.
2. The Bohemia Interactive wiki. Treat every identifier and default on a wiki page as a hint until it is found on `P:\` or in the shipped files: pages lag behind the game.
3. An archived copy of a wiki page. It is historical: it shows what the page said on the capture date, so record that date with anything taken from it.
4. Community wikis, public script browsers and tutorials. Leads only. A script browser can show another build than the one on `P:\`, and its pages can move or disappear.

Two corrections already made this way: there is no vanilla `CfgStamina` class (see the Status line), and `vonCodecQuality` goes from 0 to 30, as the shipped `serverDZ.cfg` says, not to 20.

## The Bohemia Interactive wiki

Hosts: `community.bohemia.net/wiki/...`, with `community.bistudio.com/wiki/...` as a mirror. The live site answers automated fetches with HTTP 403, so an agent usually cannot read it directly; the Wayback Machine holds copies of most DayZ pages.

Category hubs: `Category:DayZ`, then Editing, Tutorials, Official Tools, Scripting, Vehicles, Central Economy, Modelling, Modding Structure, Server, Terrain Editing and Troubleshooting.

| Topic | Wiki page |
|---|---|
| The `P:` project drive, Extract Game Data, script module order, `modded class` / `override` / `super`, file patching and packing a PBO | DayZ Modding Basics |
| Enforce Script classes, modded chains, access rules | DayZ Enforce Script Syntax |
| PBO and addon layout | DayZ Modding Structure |
| Vehicle configuration in the mission and on the server (this is not vehicle authoring: for that use the `dayz-vehicles` skill) | DayZ Vehicle Configuration |
| The diag menu | DayZ Diag Menu |
| Adding or overriding Central Economy files through `cfgeconomycore.xml` | DayZ Central Economy mission files modding |
| Central Economy on a custom terrain | Central Economy setup for custom terrains |
| The ambient spawner | CE Ambient Spawner |
| Server settings | Server Configuration, Gameplay Settings, Administration Logs, Server manager |
| Player and gear spawning, placed objects | Player Spawning, Spawning Gear, Object Spawner |
| Hazard areas, weather, underground | Contaminated Areas, Weather Configuration, Underground Areas Configuration |
| Surfaces | Surfaces |
| Error and exit codes | Error Codes, Unusual Process Exit |
| Doors and ladders on buildings | Doors on buildings, Ladders on buildings |
| Terrain work | Terrain sample, Configuring 2D Map, Generating navigation mesh, Using Road Tool in Terrain Builder, the Grass-clutter pages, Projection Layer, A2-DZ env assets lookup table |
| Buldozer | Buldozer for Object Builder, Buldozer for Terrain Builder |
| Tools | Tools Launcher, Workbench Script Debugging, Modding Samples, DayZ Tools EULA |
| A Linux server | Hosting Linux Server |

## Bohemia Interactive on GitHub

Under the `BohemiaInteractive` organisation: `DayZ-Central-Economy` (the mission and Central Economy files), `DayZ-Samples` (sample mods), `DayZ-Misc`, and `DayZ-Script-Diff` with its Experimental twin (the script tree per game version, for comparing builds). Not checked here beyond their names.

## Sources that cannot be read by an agent

- The Bohemia DayZ forums and the feedback tracker need a login; anonymous requests fail.
- Discord servers are not a source for this repo.

## What to do with a fact found outside

1. Find the symbol, key or file on `P:\` or in the shipped mission files, and cite that line.
2. If it cannot be found there, write it down marked "not yet checked on `P:\`", with the date of the page.
3. Link and summarise. Do not copy page text, README text or large class listings into the repo.

## Related notes

- `wiki-systems-reference.md`: gameplay and server configuration facts (contaminated areas, stamina and `cfggameplay.json`, diag menu, object and gear spawners, surfaces), with what was checked on `P:\`.
- `environment-and-infra.md`: server and launch infrastructure.
