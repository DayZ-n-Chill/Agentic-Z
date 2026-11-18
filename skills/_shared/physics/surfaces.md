# Surfaces

Covers what script can read about a surface (the ground, a model face, a liquid), where surfaces are defined, and what it cannot read. Water levels over river and pond objects are in `water-queries.md`; the impact sound that uses a surface is in `contact.md`.

## Where surfaces come from

`SurfaceInfo` is an "Unmanaged surface info handle" for surfaces "defined as part of 'CfgSurfaces' or exist in an objects .bisurf file", and its "Lifetime is managed in code so don't store handles of this type yourself" (`P:\scripts\3_game\surfaceinfo.c:4-5`). Get one again each time you need it.

- A terrain or interior surface is a class in `CfgSurfaces` (`P:\DZ\surfaces\config.cpp:613`) that derives from `DZ_SurfacesExt` or `DZ_SurfacesInt`. The base class sets the keys a new surface inherits: `deflection`, `friction`, `restitution`, `footDamage`, `isDigable`, `isFertile`, `chanceForCatch`, `windModifier`, `digPile`, `toolDamage` and a `Visible` class per stance (`P:\DZ\surfaces\config.cpp:647-665`).
- `SurfaceInfo.GetByName(name)` and `GetByFile(name)` look one up (`P:\scripts\3_game\surfaceinfo.c:16`, `:22`).
- A `RaycastRVResult` carries the hit face's `surface` (`P:\scripts\3_game\global\dayzphysics.c:109`).
- `Physics.GetGeomSurfaces(index, out array<SurfaceProperties> surfaces)` lists the surfaces of one geometry of a body (`P:\scripts\1_core\physics\physics.c:160`). `SurfaceProperties` itself is opaque: a class with protected constructor and destructor and nothing else (`P:\scripts\1_core\physics\surfaceproperties.c:10-15`).

## What a `SurfaceInfo` answers

All declared in `P:\scripts\3_game\surfaceinfo.c`:

| Group | Calls | Lines |
|---|---|---|
| Names | `GetName`, `GetEntryName`, `GetSurfaceType` | `:24` to `:26` |
| Physical values | `GetRoughness`, `GetDustness`, `GetBulletPenetrability`, `GetThickness`, `GetDeflection`, `GetTransparency`, `GetAudability` | `:28` to `:34` |
| Kind | `IsLiquid`, `IsStairs`, `IsPassthrough`, `IsSolid` | `:36` to `:39` |
| Effects | `GetSoundEnv`, `GetImpact`, `GetLiquidType`, the step, wheel, wheel contact and vehicle dust particle ids and sound sets, the dust kick up effects | `:41` to `:61` |

There is no friction or restitution getter. Friction and bounce are set by the physics material of each geometry and by the surface file, never from script (`rigid-body-api.md`, "Friction and bounce").

## Finding the surface at a point

On the game object (`P:\scripts\3_game\global\game.c`):

| Call | Answers | Line |
|---|---|---|
| `GetSurface(SurfaceDetectionParameters, SurfaceDetectionResult)` | The general query | `:1169` |
| `SurfaceY(x, z)` | Terrain height | `:1176` |
| `SurfaceRoadY(x, z, rsd)` and `SurfaceRoadY3D(x, y, z, rsd)` | Height of a roadway surface | `:1177`, `:1178` |
| `SurfaceGetType(x, z, out type)` and `SurfaceGetType3D` | Terrain surface name | `:1180`, `:1183` |
| `SurfaceUnderObject`, `SurfaceUnderObjectEx`, `SurfaceUnderObjectByBone` | The surface and liquid under an object | `:1184` to `:1186` |
| `SurfaceGetNormal(x, z)` | Terrain normal | `:1188` |
| `IsSurfaceDigable(surface)` and `IsSurfaceFertile(surface)` | Read `CfgSurfaces <surface> isDigable` and `isFertile` | `:1246`, `:1257` |

For the surface of an object face, use `DayZPhysics.GetHitSurface` or `GetHitSurfaceAndLiquid` (`P:\scripts\3_game\global\dayzphysics.c:204`, `:206`). They need an object, so they name nothing on open terrain; see `layers-and-raycasts.md`, "Surface under a point".
