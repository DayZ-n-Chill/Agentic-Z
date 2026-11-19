# Animal territories

Covers the mission files that say where animals and ambient life live: `cfgenvironment.xml`, the `env\*_territories.xml` zone files it registers, the behaviour names it binds, and the group templates on `P:\` those names select.

The server lead and `dayz-server-admin` own these files; the AI worker hands over the entries (`spawning-and-performance.md`). The mission files ship with DayZ Server in `mpmissions\dayzOffline.chernarusplus\`, and `/dayz-add-server` copies them into `.server/<instance>/mission/`. Vanilla copies of each map's files are also on `P:\` under `P:\DZ\worlds\<map>\ce\` (`chernarusplus`, `enoch`, `sakhal`, `nasdara`). Lines below cite the ChernarusPlus copy, `P:\DZ\worlds\chernarusplus\ce\`; a short `cfgenvironment.xml:<line>` means `P:\DZ\worlds\chernarusplus\ce\cfgenvironment.xml`. Grep the element name when an update moves it. Spawn rates in play, what each group decides at run time and how it uses the navmesh are engine behaviour and not covered here.

## How `cfgenvironment.xml` is laid out

The root is `<env>` (`P:\DZ\worlds\chernarusplus\ce\cfgenvironment.xml:2`), and its only child in vanilla is `<territories>` (`:5` to `:114`).

Inside `<territories>` the zone files come first, one empty `<file path="env/..."/>` per file: cattle, sheep and goat, red deer, roe deer, wild boar, pig, hen, wolf, hare, zombie, bear and fox (`:7` to `:19`). Vanilla registers `env/hare_territories.xml` twice, at `:15` and `:18`; nothing shows what the engine does with the duplicate.

Each territory binding then names a group kind, a display name and a behaviour, and points at one registered zone file by its stem:

```xml
<territory type="Herd" name="Deer" behavior="DZDeerGroupBeh">
    <file usable="red_deer_territories" />
</territory>
```

That is `P:\DZ\worlds\chernarusplus\ce\cfgenvironment.xml:21` to `:23`. The `usable` value is the file stem, not the `env/red_deer_territories.xml` path used to register it.

## Herd, Ambient and the ZombieTest entry

The animal `Herd` block (`:21` to `:47`) declares nine territories: Deer, Cow, Goat, Sheep, RoeDeer, Wolf, WildBoar, Pig and Bear. Each holds only its `<file usable="..."/>` line, with no `<agent>`, `<spawn>` or `<item>` child.

The three `Ambient` territories after it do declare agents: `AmbientHen` (`:50` to `:67`), `AmbientHare` (`:70` to `:80`) and `AmbientFox` (`:83` to `:93`). Each carries `<agent>` children with `<spawn>` class names, and `<item>` values at territory level.

`ZombieTest` shows that a `Herd` territory can carry agents too. It is `<territory type="Herd" name="ZombieTest" behavior="DZdomesticGroupBeh">` (`:96`) with `<file usable="zombie_territories" />` (`:97`), and it declares `<agent type="Male">` (`:99`) and `<agent type="Female">` (`:104`), neither with a `chance`. Infected zones are covered in `spawning-and-performance.md`, infected classes in `creatures.md` and `custom-infected.md`.

## Agents, spawns and items

An `Ambient` agent groups the classes one agent type can spawn. In `AmbientHen`:

| Element | Line | Spawns |
|---|---|---|
| `<agent type="Male" chance="1">` | `:53` | `Animal_GallusGallusDomesticus`, chance 1 (`:54`) |
| `<agent type="Female" chance="3">` | `:56` | `Animal_GallusGallusDomesticusF_Brown` chance 1, `_Spotted` chance 10, `_White` chance 20 (`:57` to `:59`) |

`AmbientHare` repeats the shape with `Animal_LepusEuropaeus` (`:73` to `:78`), and `AmbientFox` with `Animal_VulpesVulpes` (`:86` to `:91`).

`<item name="..." val="..."/>` at territory level tunes an `Ambient` entry:

| Territory | Items |
|---|---|
| `AmbientHen` | `globalCountMax` 50, `zoneCountMin` 1, `zoneCountMax` 1, `playerSpawnRadiusNear` 25, `playerSpawnRadiusFar` 75 (`:62` to `:66`) |
| `AmbientHare` | `zoneTouchDisableEditPeriodSec` 300 (`:79`) |
| `AmbientFox` | `zoneTouchDisableEditPeriodSec` 450 (`:92`) |

`ZombieTest` places its items differently. Each agent holds `countMin` 0 and `countMax` 0 (`:101` and `:102` for Male, `:106` and `:107` for Female) under a spawn with no `chance` (`ZombieMale3_NewAI` at `:100`, `ZombieFemale3_NewAI` at `:105`). At territory level it sets `herdsCount` 0 (`:111`), under the vanilla comment "count of herds of this type in the map" (`:110`).

## Zone files

A zone file has the root `<territory-type>`, one `<territory color="...">` per territory, and one self closing zone per zone. The first wolf zone (`P:\DZ\worlds\chernarusplus\ce\env\wolf_territories.xml:4`):

```xml
<zone name="Water" smin="0" smax="0" dmin="0" dmax="0" x="10597.5" z="13432.5" r="60"/>
```

| File | Territories | Zone names | Lines |
|---|---|---|---|
| `env\wolf_territories.xml` | 24 | `Water` (`:4`), `Rest` (`:5`), `HuntingGround` (`:9`), repeated to `:325`; every zone has `smin`, `smax`, `dmin` and `dmax` at 0 | root `:2` to `:327` |
| `env\bear_territories.xml` | 13 | `Graze` only (first at `:4`, for example `:12`, `:55`, `:92`) | root `:2` to `:100` |

The first territory in each file opens at `:3`: `<territory color="4291611852">` in the wolf file and `<territory color="4294923520">` in the bear file.

Never copy zone names from one species to another: wolves use `Water`, `Rest` and `HuntingGround`, bears use `Graze`. The other zone files are not covered here.

## Behaviour names and the templates they select

The `behavior` values in `cfgenvironment.xml`, spelled as vanilla spells them:

| Behaviour | Territories | Template | `type` | Zone types its life cycle names |
|---|---|---|---|---|
| `DZDeerGroupBeh` | Deer (`:21`), RoeDeer (`:33`), WildBoar (`:39`) | `P:\DZ\data\aiconfigs\config.cpp:151` | `WildHerbivores` (`:153`) | `Graze` (`:173`), `Rest` (`:179`), `Water` (`:197`) |
| `DZdomesticGroupBeh` | Cow (`:24`), `ZombieTest` (`:96`) | `P:\DZ\data\aiconfigs\config.cpp:201` | `DomesticHerbivores` (`:203`) | `Rest` (`:224`), `Water` (`:230`), `Graze` (`:236`) |
| `DZSheepGroupBeh` | Goat (`:27`), Sheep (`:30`), Pig (`:42`) | `P:\DZ\data\aiconfigs\config.cpp:252` | `DomesticHerbivores` (`:254`) | `Rest` (`:276`), `Graze` (`:282`) |
| `DZWolfGroupBeh` | Wolf (`:36`) | `P:\DZ\data\aiconfigs\config.cpp:87` | `Predators` (`:89`) | `Rest` (`:127`, `:140`), `HuntingGround` (`:133`, `:146`) |
| `BlissBearGroupBeh` | Bear (`:45`) | `P:\DZ\data_bliss\aiconfigs\config.cpp:9` | `Bear` (`:11`) | `Graze` (`:24` to `:48`) |
| `DZAmbientLifeGroupBeh` | `AmbientHen` (`:50`), `AmbientHare` (`:70`), `AmbientFox` (`:83`) | `P:\DZ\data\aiconfigs\config.cpp:79` | `AmbientLifeGroup` (`:81`) | none |

The second column cites `cfgenvironment.xml`; the rest cite the template file. The bear's name is `BlissBearGroupBeh`, not `DZBearGroupBeh`. All templates sit in `class GroupBehaviourTemplates` (`P:\DZ\data\aiconfigs\config.cpp:77`).

The `zoneType` values in a template's life cycle (`class LifeCycleDayTime` at `P:\DZ\data\aiconfigs\config.cpp:121` for the wolf) are the same words as the zone names in that species' file: the bear template names only `Graze` and the bear file holds only `Graze`; the wolf template names `Rest` and `HuntingGround`, and the wolf file holds those plus `Water`. So a new territory file needs the zone names of the template it binds. That the engine matches them by name is what the two files show; it is not tested in game.

The creature side of the link: an animal's behaviour template names its group template with `defaultGroupTemplateName` (`behaviour-config.md`), for example the bear at `P:\DZ\AI_bliss\config.cpp:20`. What a group behaviour does at run time is engine code, so never infer it from a territory's name.

## Nasdara

The Nasdara mission registers its own zone files, among them `env/mouflon_territories.xml`, `env/monitor_territories.xml` and `env/dobermann_shepherd_territories.xml` (`P:\DZ\worlds\nasdara\ce\cfgenvironment.xml:9`, `:13` and `:15`). Its `Dog` herd binds `DZDogGroupBeh` (`:32`), and the monitor lizard is an `Ambient` territory, `AmbientLizard`, spawning `Animal_VaranusGriseus` (`:83` to `:90`). The `Mouflon` herd binds `DZSheepGroupBeh` (`:26`), not the `DZMouflonGroupBeh` its creature template names (`P:\DZ\AI_takistan\config.cpp:1342`). Which of the two the engine runs for a spawned mouflon is not checked on `P:\`; both name only `Graze` and `Rest` zones. Both Nasdara templates are in `P:\DZ\data_takistan\aiconfigs\config.cpp` (`patrols-and-guards.md`).

## The economy entry

A `<spawn configName="Animal_...">` names a class, and the class also needs an entry in the mission's `db\types.xml`, which holds lifetimes and counts. Vanilla has one for each of the six `Animal_` classes the `Ambient` territories name, from `Animal_GallusGallusDomesticus` (`P:\DZ\worlds\chernarusplus\ce\db\types.xml:1605`) to `Animal_VulpesVulpes` (`:1755`). The two `ZombieTest` classes have no `types.xml` entry, and their counts in `cfgenvironment.xml` are 0. More on the economy files: `spawning-and-performance.md` and `_shared/enscript/integrations/central_economy.md`.

## Adding an animal territory to a mission

1. Add a zone file such as `env/my_animal_territories.xml`: the root `<territory-type>`, one `<territory color="...">` per territory, and `<zone name="..." smin="..." smax="..." dmin="..." dmax="..." x="..." z="..." r="..."/>` entries whose names are the zone types of the behaviour you bind.
2. Register it inside `<territories>` with `<file path="env/my_animal_territories.xml"/>`.
3. Add a `<territory type="Herd" ...>` or `<territory type="Ambient" ...>` binding with `<file usable="my_animal_territories"/>`, the stem. For an `Ambient` binding add the `<agent>`, `<spawn>` and `<item>` children shown above.
4. Check that every `<spawn configName="Animal_...">` class has a `db\types.xml` entry.
5. Restart the server and read the RPT for errors that name the new file, territory or class.

This is the shape vanilla uses; no vanilla file shows a load or spawn order, so none is claimed.
