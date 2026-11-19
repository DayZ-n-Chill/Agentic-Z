# Effects from script

How a mod registers its own `.ptc` files, plays a layered effect at a position or through the effect manager, and turns single emitters on and off as the game changes. The examples come from the plane effects of `layered-effects.md`; `m_PlaneMode`, `PlaneMode`, `GetPlaneSpeed()` and `PLANES_SEAPLANE_FRONT` belong to that mod. The full signatures are in `script-api-reference.md`.

## Contents

- [Registering the effects](#registering-the-effects)
- [Playing them](#playing-them)
- [Turning single emitters on and off](#turning-single-emitters-on-and-off)

## Registering the effects

The plane mod registers its three files in a modded `ParticleList`, in the `3_Game` script module:

```c
// MyMod/scripts/3_Game/ParticleList.c
modded class ParticleList
{
    static const int PLANES_EX = RegisterParticle("MyMod/graphics/", "PLANES_EX");
    static const int PLANES_IMPACT = RegisterParticle("MyMod/graphics/", "PLANES_IMPACT");
    static const int PLANES_BOOM = RegisterParticle("MyMod/graphics/", "PLANES_BOOM");
}
```

- The first argument is the mod folder that holds the file, with a slash at the end.
- The second is the file name without `.ptc`.
- Each call returns the ID to store in a `static const int`.
- `RegisterParticle(string root_path, string file_name)` lowercases both arguments (`P:\scripts\3_game\particles\particlelist.c:452`), so the upper case names here work; this skill still writes lower case names with the mod prefix (`SKILL.md`, "Registering custom particles").

## Playing them

A one shot at a world position, when a plane hits the ground. `EOnContact` is the vanilla contact event (`P:\scripts\1_core\proto\enentity.c:213`) and `Particle.PlayInWorld` the vanilla factory (`P:\scripts\3_game\particles\particle.c:174`):

```c
override void EOnContact(IEntity other, Contact extra)
{
    if (m_PlaneMode == PlaneMode.PLANE_MODE_AIR && GetVelocity(this).Length() > 30)
    {
        Particle p = Particle.PlayInWorld(ParticleList.PLANES_IMPACT, extra.Position);
    }
}
```

Through an `EffectParticle`, so the effect manager owns it:

```c
EffectParticle eff = new EffectParticle();
eff.SetParticleID(ParticleList.PLANES_BOOM);
eff.SetAutodestroy(true);
SEffectManager.PlayInWorld(eff, GetPosition());
```

- The ID setter is `SetParticleID(int id)` (`P:\scripts\3_game\effects\effectparticle.c:327`). Do not write `SetParticle(ParticleList.PLANES_BOOM)`: vanilla `SetParticle` takes a `Particle` object, not an ID (`effectparticle.c:138`).
- `SetAutodestroy` is declared on `Effect` (`P:\scripts\3_game\effect.c:242`).
- `SEffectManager.PlayInWorld` takes the effect and a position (`P:\scripts\3_game\effectmanager.c:47`).
- Enforce Script has no `import` statement; never open the snippet with `import "EffectParticle";`.

## Turning single emitters on and off

An effect can react to the game by switching its emitters. A seaplane water effect that copies the vanilla boat wake:

```c
// Seaplane example. GetPlaneSpeed() and PLANES_SEAPLANE_FRONT are the mod's own.
class EffectSeaplaneWaterFront : EffectBoatWaterBase
{
    void EffectSeaplaneWaterFront()
    {
        SetParticleState(ParticleList.PLANES_SEAPLANE_FRONT);
    }

    override void Update(float timeSlice = 0)
    {
        super.Update(timeSlice);

        float speed = GetPlaneSpeed();
        UpdateSpeedState(GetParticle(), speed);
    }

    override protected void UpdateSpeedState(Particle ptc, float speed)
    {
        // Emitter 0 is the slow wake, 1 the medium one, 2 the fast one.
        EnableEmitor(ptc, 0, speed > 5.0);
        EnableEmitor(ptc, 1, speed > 15.0);
        EnableEmitor(ptc, 2, speed > 30.0);
    }
}
```

What vanilla gives you for this:

| Member | What it is | Source |
|---|---|---|
| `EnableEmitor(Particle ptc, int id, bool enable)` | A protected method of `EffectBoatWaterBase`, not of `EffectParticle`. It sets `BIRTH_RATE` and `BIRTH_RATE_RND` of one emitter to zero, or back to the `.ptc` values. Extend `EffectBoatWaterBase` as above, or copy the method into your own `EffectParticle` subclass. | `P:\scripts\4_world\entities\effects\boatwatereffects.c:306` |
| `GetParticle()` | The current particle of an effect. Vanilla has no `GetCurrentParticle()`. | `P:\scripts\3_game\effects\effectparticle.c:166` |
| `UpdateSpeedState(Particle ptc, float speed)` | The hook the vanilla front wake overrides. | `boatwatereffects.c:24` |
| `Update(float timeSlice = 0)` | Declared on `EffectBoatWaterBase` too; `EffectParticle` has none, so `override void Update` on a direct `EffectParticle` subclass does not compile. | `boatwatereffects.c:325` |

Nothing calls `Update` for you: the vanilla boat calls it on each water effect every frame (`P:\scripts\4_world\entities\vehicles\boatscript.c:815`), and a plane has to do the same.

`modded class` rules and the language itself are in `_shared/enscript/patterns/modded_class.md` and the Enforce Script pack (`_shared/enscript/depth/`).
