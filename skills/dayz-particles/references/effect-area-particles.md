# Effect area particles: emitter budget and vertical band

How many particle emitters a contaminated area in `cfgeffectarea.json` asks for, the hard cap, and why an area can hurt players where no gas is drawn. Run these checks before you choose a large radius. Line numbers are from the 1.30 scripts on `P:\`.

## Contents

- [The hard cap](#the-hard-cap)
- [Which JSON keys feed which routine](#which-json-keys-feed-which-routine)
- [The budget formula for a static area](#the-budget-formula-for-a-static-area)
- [What the pool error means](#what-the-pool-error-means)
- [The vertical band](#the-vertical-band)
- [Safe positions](#safe-positions)
- [The JSON schema](#the-json-schema)
- [Checklist before picking a radius](#checklist-before-picking-a-radius)

## The hard cap

Each effect area may place at most 1,000 emitters: `PARTICLES_MAX = 1000` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:85`). `SpawnParticles` stops adding emitters once `count` reaches `PARTICLES_MAX` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:425`).

Reaching the cap does not shrink the damage radius. The trigger keeps its full size, so the area stays lethal beyond the drawn gas. A valid JSON file and a server that boots do not prove the edge of the area is visible.

## Which JSON keys feed which routine

The loader copies the JSON keys into the area's parameters: `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`, `OuterPartDist`, `OuterOffset` and `VerticalLayers` (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarealoader.c:57` to `:62`).

- A static area (`ContaminatedArea_Static`, declared at `P:\scripts\4_world\classes\contaminatedarea\contaminatedarea.c:33`) fills itself with `FillWithParticles(m_Position, m_Radius, m_OuterRingOffset, m_InnerSpacing, m_ParticleID)` (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarea.c:70`). Only `InnerPartDist` (`m_InnerSpacing`) and `OuterOffset` (`m_OuterRingOffset`) reach it.
- A dynamic area calls `PlaceParticles` with `m_InnerRings`, `m_InnerSpacing`, `m_OuterRingToggle`, `m_OuterSpacing` and `m_OuterRingOffset` (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarea_dynamicbase.c:74`).

So for a static area `InnerRingCount`, `OuterPartDist` and `OuterRingToggle` do nothing. Do not tune them to fix the density of a static area.

## The budget formula for a static area

`FillWithParticles` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:335`) lays emitters on rings around a centre emitter. For the normal large area, where `R >= 1.25 * s`, the upper budget is:

```text
R = Radius + OuterOffset
s = max(InnerPartDist, 1)
N = ceil((R - s/2) / s)
d = (R - s/2) / N
XZ = 1 + sum(floor(2 * PI2 * d * k / s), k = 1..N)
budget_max = XZ * (VerticalLayers + 1)
```

Where each line comes from:

- `s`: a `partSize` of zero or less becomes 1 (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:346`).
- `N` and `d`: `ringCount = Math.Ceil(radiusMax / partSize)` and `ringDist = radiusMax / ringCount`, after `radiusMax` was reduced by half a particle (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:372` and `P:\scripts\4_world\classes\contaminatedarea\effectarea.c:373`).
- The ring count per ring: `circumference = 2 * Math.PI2 * ringRadius`, then `Math.Floor(circumference / partSize)` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:390`).
- `PI2` is already two pi, `6.28318530717958` (`P:\scripts\1_core\proto\enmath.c:13`). The vanilla line therefore uses about `4 * pi * r`, twice the true circumference. Budgeting with `2 * pi * r` under-counts by half.
- The leading `1` is the centre emitter. The `VerticalLayers + 1` factor is the layer loop in `SpawnParticles`, which runs from layer 0 to `m_VerticalLayers` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:420`).

Small areas take two other branches: an area not larger than `radiusPart * 1.5` gets only the centre emitter, and one smaller than `radiusPart * 2.5` gets one ring and no centre emitter (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:361` and `P:\scripts\4_world\classes\contaminatedarea\effectarea.c:363`). Read those branches directly instead of using the formula.

Worked check: `Radius=500`, `OuterOffset=20`, `InnerPartDist=70` and `VerticalLayers=1` give `N=7`, `d=69.286`, `XZ=346` and `budget_max=692`, which is under the cap.

Raising `InnerPartDist` lowers the number of rings `N`. It does not thin out the emitters on a ring that already exists.

A rougher form of the budget, `emitters ~= 6.283 * N^2 * (VerticalLayers + 1)`, under-counts (616 against 692 in the worked check), and an estimate that under-counts cannot approve a radius. Use the formula above.

## What the pool error means

`Not enough particles in pool for EffectArea` is raised in `InsertParticles`, when `ParticleManager` returned fewer particles than the count asked for (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:444`). It is not the cap message: reaching `PARTICLES_MAX` only stops `SpawnParticles` from adding more, with no log line. Do not use the RPT message to decide whether a radius is within the cap. Work out `budget_max`, keep it under 1,000 with margin, and look at the edge of the area in game.

## The vertical band

The trigger is a cylinder of limited height: `SetCollisionCylinderTwoWay(radius, -(m_NegativeHeight + centerHeightCorrection), (m_PositiveHeight - centerHeightCorrection))`, where `centerHeightCorrection` is `(m_PositiveHeight - m_NegativeHeight) * 0.5` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:501`).

Emitters are kept only inside the same band: `Math.IsInRange(partPos[1], centerPos[1] - m_NegativeHeight, centerPos[1] + m_PositiveHeight)` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:425`). This culling can make the real count lower than `budget_max`.

Choose `PosHeight` and `NegHeight` from the real height range of the terrain inside the radius, not from a small vanilla zone.

Underground spaces count too:

- In 1.29 a particle was snapped to `SurfaceY`, so none was ever placed below the terrain, and a bunker inside the cylinder could be lethal while showing no gas (1.29 is not checked on `P:\`, which holds 1.30).
- Since 1.30 a particle starts at the height of the area centre and is lowered to `SurfaceRoadY` only when it is above the road surface (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:414`). An area centred below the surface keeps its particles at that height.

A lethal space with no gas can be a deliberate design, but it should never happen by accident.

## Safe positions

`SafePositions` is one global list in the JSON, not a list per area (`P:\scripts\4_world\classes\contaminatedarea\jsondatacontaminatedarea.c:5`).

- `TeleportCheck` moves a player who has just connected inside an area, and was not in one when they logged out, to the closest safe position (`P:\scripts\4_world\static\miscgameplayfunctions.c:1767`). The area exposure modifier calls it (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\areaexposure.c:44`).
- `GetClosestSafePos` searches the whole list and measures in two dimensions only (`P:\scripts\4_world\static\miscgameplayfunctions.c:1794`).
- Each entry is two numbers, x then z: the second number is read as z (`miscgameplayfunctions.c:1801` and `:1802`), and the player is put on the terrain there with `SurfaceY` (`:1779`). A safe position written as `[x, y, z]` sends players to the wrong place, and one above a bunker or under a roof puts them on the terrain, not on the floor.

After any change of radius, measure every safe position against every area. A rescue point that lies inside another area's cylinder moves a reconnecting player from gas to gas.

## The JSON schema

`JsonDataAreaData` is the authority for the keys of one area: `Pos`, `Radius`, `PosHeight`, `NegHeight`, `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`, `OuterPartDist`, `OuterOffset`, `VerticalLayers`, `VerticalOffset`, `ParticleName`, `EffectInterval`, `EffectDuration` and `EffectModifier` (`P:\scripts\4_world\classes\contaminatedarea\jsondatacontaminatedarea.c:17` to `:34`).

Keys named `InnerRingRatio` and `OuterRingRatio` appear in some `cfgeffectarea.json` files. They are not in that class and no vanilla script reads them.

`InnerRingCount`, `InnerPartDist`, `OuterPartDist`, `OuterOffset`, `VerticalLayers`, `VerticalOffset`, `EffectInterval` and `EffectDuration` are declared `int`, so write whole numbers (`jsondatacontaminatedarea.c:23` to `:32`); what the loader does with a fraction is not checked on `P:\`. The player side particles of an area are named per area in `PlayerData`: `AroundPartName`, `TinyPartName` and `PPERequesterType` (`jsondatacontaminatedarea.c:36` to `:40`).

`FillWithParticles` returns at once in a build compiled with `NO_GUI` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:339` to `:341`), so a server without a GUI places no emitters and the budget only matters on clients.

Height values for a large radius stay unconfirmed until the real terrain and any underground depth have been measured in game.

## Checklist before picking a radius

1. Work out `budget_max` with the formula and keep it under 1,000 with margin.
2. Measure the lowest and highest ground inside the radius, including any underground space, and set `PosHeight` and `NegHeight` to cover it.
3. Compare every entry of the global `SafePositions` list against every area.
4. Look at the edge of the area in game: the gas should reach the place where damage starts.
