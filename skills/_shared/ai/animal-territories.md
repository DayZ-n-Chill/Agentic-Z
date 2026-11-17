# Animal territories and ambient life

The mission files that register where animals and ambient life can live: `cfgenvironment.xml`, the `env\*_territories.xml` zone files it points at, the exact group behaviour names the vanilla file uses, and the group templates on `P:\` those names select. It records what the vanilla files show. Spawn rates in play, what each group decides at run time and navmesh behaviour are not claimed here.

The mission files ship with DayZ Server in `mpmissions\dayzOffline.chernarusplus\` (copied into `.server/<instance>/mission/` by `/dayz-add-server`); they are not on `P:\`. Lines below were read in that vanilla mission of the installed server (Steam build `26220720`):

- `cfgenvironment.xml`, 115 lines, SHA-256 `3f73c9f3abe7ed3811811a147ecfcc596af6170552e372c5eaff27dd92fbf135`.
- `env\wolf_territories.xml`, 327 lines, SHA-256 `36738538717e378a13e0566b9888e58d06a80193506d8bd5a12bf57949aad935`.
- `env\bear_territories.xml`, 100 lines, SHA-256 `9aa16e734d49d70e835ebe8161f59f0d2386602f9cfc026b42471a1826a9bbf8`.

Line numbers are those files'; check them again before citing them for another build or another map. The server lead and `dayz-server-admin` own these files; the AI worker hands over the entries (`spawning-and-performance.md`).

## 1. The shape of `cfgenvironment.xml`

The document root is `<env>` (`cfgenvironment.xml:2`) and its only child in the vanilla file is `<territories>` (`:5`), closed at `:114`; `</env>` is at `:115`.

Inside `<territories>`, zone files are registered first, one empty `<file path="env/..."/>` element per file: `env/cattle_territories.xml` (`:7`), `env/sheep_goat_territories.xml` (`:8`), `env/red_deer_territories.xml` (`:9`), `env/roe_deer_territories.xml` (`:10`), `env/wild_boar_territories.xml` (`:11`), `env/pig_territories.xml` (`:12`), `env/hen_territories.xml` (`:13`), `env/wolf_territories.xml` (`:14`), `env/hare_territories.xml` (`:15`), `env/zombie_territories.xml` (`:16`), `env/bear_territories.xml` (`:17`) and `env/fox_territories.xml` (`:19`).

A territory binding then names a group kind, a display name and a behaviour, and points at one registered zone file by its stem:

```xml
<territory type="Herd" name="Deer" behavior="DZDeerGroupBeh">
    <file usable="red_deer_territories" />
</territory>
```

That is `cfgenvironment.xml:21-23`. The `usable` value is the file stem (`red_deer_territories`), not the `env/red_deer_territories.xml` path used at registration.

One oddity, recorded as written with no run time meaning read into it: `env/hare_territories.xml` is registered twice, at `:15` and again at `:18`.

## 2. `Herd` against `Ambient`, and the `ZombieTest` exception

The animal `Herd` block, `cfgenvironment.xml:21-47`, declares nine territories (Deer, Cow, Goat, Sheep, RoeDeer, Wolf, WildBoar, Pig and Bear). None of them declares an `<agent>`, a `<spawn>` or an `<item>` child; each holds only its `<file usable="..."/>` line, as in the Deer example.

The three `Ambient` territories that follow do declare agents: `AmbientHen` (`:50-67`), `AmbientHare` (`:70-80`) and `AmbientFox` (`:83-93`) each carry `<agent>` children with `<spawn>` class names, and `<item>` values at territory level (section 3). Read the contrast narrowly: it is a fact about the animal `Herd` block at `:21-47` and the `Ambient` entries at `:50-93` of this file, not a rule that a `Herd` territory never declares agents.

`ZombieTest` is the counterexample in the same file. It is a `Herd` territory (`:96-112`, `<territory type="Herd" name="ZombieTest" behavior="DZdomesticGroupBeh">` at `:96`, `<file usable="zombie_territories" />` at `:97`) and it does declare agents: `<agent type="Male">` at `:99` and `<agent type="Female">` at `:104`, neither with a `chance` attribute.

The `zombie_territories.xml` registration at `:16` is the infected counterpart of the animal zone files; infected zones are covered in `spawning-and-performance.md`, and infected classes in `creatures.md` and the dayz-characters skill.

## 3. `<agent>`, `<spawn>` and `<item>`

An `Ambient` agent groups the class names one agent type can spawn. In `AmbientHen`, `<agent type="Male" chance="1">` (`:53`) holds `<spawn configName="Animal_GallusGallusDomesticus" chance="1" />` (`:54`), and `<agent type="Female" chance="3">` (`:56`) holds three spawns (`:57-59`): `Animal_GallusGallusDomesticusF_Brown` chance 1, `Animal_GallusGallusDomesticusF_Spotted` chance 10, `Animal_GallusGallusDomesticusF_White` chance 20. `AmbientHare` repeats the shape with `Animal_LepusEuropaeus` (`:73-78`), and `AmbientFox` with `Animal_VulpesVulpes` (`:86-91`).

`<item name="..." val="..."/>` values at territory level tune the `Ambient` entries. `AmbientHen` declares `globalCountMax` 50 (`:62`), `zoneCountMin` 1 (`:63`), `zoneCountMax` 1 (`:64`), `playerSpawnRadiusNear` 25 (`:65`) and `playerSpawnRadiusFar` 75 (`:66`). `AmbientHare` declares only `zoneTouchDisableEditPeriodSec` 300 (`:79`), and `AmbientFox` only `zoneTouchDisableEditPeriodSec` 450 (`:92`).

`ZombieTest` places its `<item>` elements differently. Inside each agent, `<item name="countMin" val="0" />` and `<item name="countMax" val="0" />` sit at `:101-102` (Male) and `:106-107` (Female), under spawns with no `chance` attribute (`ZombieMale3_NewAI` at `:100`, `ZombieFemale3_NewAI` at `:105`). At territory level it declares `<item name="herdsCount" val="0" />` (`:111`), under the source comment `<!-- count of herds of this type in the map -->` (`:110`). The agent level `countMin` and `countMax` and the territory level `herdsCount` are the `ZombieTest` shape; the `Ambient` entries show no such items.

## 4. Zone files: `env\*_territories.xml`

A zone file has the root `<territory-type>`, one `<territory color="...">` element per territory, and one self closing zone element per zone:

```xml
<zone name="Water" smin="0" smax="0" dmin="0" dmax="0" x="10597.5" z="13432.5" r="60"/>
```

That is the first zone of `wolf_territories.xml` (`env\wolf_territories.xml:4`). The root opens at `:2`, the first `<territory color="4291611852">` at `:3`, and the root closes at `:327`; the file holds 24 territories.

Wolf zone names in this file are `Water` (first at `:4`), `Rest` (`:5`) and `HuntingGround` (`:9`), repeated through `:4-326`. Every wolf zone carries `smin="0" smax="0" dmin="0" dmax="0"` with its own `x`, `z` and `r`.

Bear zones use another name. `bear_territories.xml` opens its root at `env\bear_territories.xml:2`, its first `<territory color="4294923520">` at `:3` and its first `<zone name="Graze" .../>` at `:4`. The file closes at `:100` and holds 13 territories; every zone in it is a `Graze` zone (for example `:12`, `:55`, `:92`).

Do not carry zone names from one species to another: wolves use `Water`, `Rest` and `HuntingGround`, bears use `Graze`. Other `env\*_territories.xml` files were not read for this note.

## 5. Behaviour names and the templates they select

The `behavior="..."` values in the vanilla file, spelled exactly as written there:

- `DZDeerGroupBeh`: Deer (`:21`), RoeDeer (`:33`), WildBoar (`:39`).
- `DZdomesticGroupBeh`: Cow (`:24`), `ZombieTest` (`:96`).
- `DZSheepGroupBeh`: Goat (`:27`), Sheep (`:30`), Pig (`:42`).
- `DZWolfGroupBeh`: Wolf (`:36`).
- `BlissBearGroupBeh`: Bear (`:45`). The vanilla spelling is `BlissBearGroupBeh`, not `DZBearGroupBeh`.
- `DZAmbientLifeGroupBeh`: `AmbientHen` (`:50`), `AmbientHare` (`:70`), `AmbientFox` (`:83`).

Each name is a group template class on `P:\`, in `class GroupBehaviourTemplates`:

| Behaviour name | Template | `type` | Zone types its life cycle names |
|---|---|---|---|
| `DZAmbientLifeGroupBeh` | `P:\DZ\data\aiconfigs\config.cpp:79` | `AmbientLifeGroup` (`:81`) | none |
| `DZWolfGroupBeh` | `P:\DZ\data\aiconfigs\config.cpp:87` | `Predators` (`:89`) | `Rest` (`:127`, `:140`), `HuntingGround` (`:133`, `:146`) |
| `DZDeerGroupBeh` | `P:\DZ\data\aiconfigs\config.cpp:151` | `WildHerbivores` (`:153`) | `Graze` (`:173`), `Rest` (`:179`), `Water` (`:197`) |
| `DZdomesticGroupBeh` | `P:\DZ\data\aiconfigs\config.cpp:201` | `DomesticHerbivores` (`:203`) | `Rest` (`:224`), `Water` (`:230`), `Graze` (`:236`) |
| `DZSheepGroupBeh` | `P:\DZ\data\aiconfigs\config.cpp:252` | `DomesticHerbivores` (`:254`) | `Rest` (`:276`), `Graze` (`:282`) |
| `BlissBearGroupBeh` | `P:\DZ\data_bliss\aiconfigs\config.cpp:9` | `Bear` (`:11`) | `Graze` (`:24` to `:48`) |

The zone type names in a template's life cycle (`zoneType`, inside `class LifeCycleDayTime` at `P:\DZ\data\aiconfigs\config.cpp:121` for the wolf) are the same words as the zone `name` values in that species' territory file: the bear template names only `Graze` and the bear file holds only `Graze` zones; the wolf template names `Rest` and `HuntingGround`, and the wolf file holds those plus `Water`. So the zone names a new territory file needs are the `zoneType` values of the template it is bound to. That the engine matches them by name is the reading the two files support; it was not tested in game.

The creature side of the same link: an animal's behaviour template names its default group template with `defaultGroupTemplateName` (`behaviour-config.md`), for example the bear at `P:\DZ\AI_bliss\config.cpp:20`.

This file records the wiring only. What each group behaviour does at run time is engine code; do not infer it from a territory's name. The Nasdara data of 1.30 has two more templates (`DZMouflonGroupBeh`, `DZDogGroupBeh`), not yet checked on `P:\`; see `patrols-and-guards.md`.

## 6. The Central Economy entry

A `<spawn configName="Animal_...">` names a class; the territory file itself shows no Central Economy dependency. The class also needs an entry in the mission's `db\types.xml`, the file that holds lifetimes and counts: vanilla has one for each of the six `Animal_` classes the `Ambient` territories name, from `<type name="Animal_GallusGallusDomesticus">` at `db\types.xml:1605` to `Animal_VulpesVulpes` at `:1755` of the same mission. The two `ZombieTest` classes, `ZombieMale3_NewAI` and `ZombieFemale3_NewAI`, have no `types.xml` entry there, and their counts in `cfgenvironment.xml` are 0. Treat the `types.xml` entry as the economy record for the class, not as a condition the territory file proves. More on the economy files: `spawning-and-performance.md` and `skills/_shared/enscript/integrations/central_economy.md`.

## 7. Adding an animal territory to a custom mission

Following the vanilla shape above, and claiming no run time ordering beyond it:

1. Add a zone file, for example `env/my_animal_territories.xml`, with the root `<territory-type>`, one `<territory color="...">` per territory, and `<zone name="..." smin="..." smax="..." dmin="..." dmax="..." x="..." z="..." r="..."/>` entries whose `name` values are the zone types of the behaviour you will bind (section 5; do not copy wolf or bear names blindly).
2. Register the file inside `<territories>` in `cfgenvironment.xml` with `<file path="env/my_animal_territories.xml"/>`, as at `:7-19`.
3. Add a `<territory type="Herd|Ambient" name="..." behavior="...">` binding. The animal `Herd` examples carry only `<file usable="my_animal_territories"/>` (the file stem, not the full path), as at `:21-23`; `ZombieTest` shows a `Herd` can also carry agents (section 2). For an `Ambient` binding, add the `<agent>`, `<spawn>` and `<item>` children shown in section 3.
4. Check that every `<spawn configName="Animal_...">` class has an entry in the mission's `db\types.xml` (section 6).
5. Restart the server and read the RPT for territory or economy errors that name the new file, territory or class.

No step claims a load or spawn order; the list records only the registration shape the vanilla file uses.

## Limits

- Vanilla ChernarusPlus only, DayZ Server build `26220720`, the three files listed at the top.
- Nothing here was measured in game. The duplicate `hare_territories.xml` registration (`:15`, `:18`) is a fact about the text, not a claim about what the engine does with a duplicate.
- The territory counts (24 wolf, 13 bear) and the reading that bear zones are all `Graze` cover the two zone files listed; other `env\*_territories.xml` files were not read.
