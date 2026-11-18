# Choosing and tuning device particles

Which vanilla particles suit a placed device and whether each one needs stopping, how to tune a particle after it starts, and how to bring older device code up to the DayZ 1.30 form. The device classes these build on, starting with `MyMod_DeviceBase`, are in `integration-patterns.md`.

## Contents

- [Vanilla particles for placed devices](#vanilla-particles-for-placed-devices)
- [Pattern E: Parameter tuning at runtime](#pattern-e-parameter-tuning-at-runtime)
- [Bringing older device code up to date](#bringing-older-device-code-up-to-date)

## Vanilla particles for placed devices

Every constant below is registered in `P:\scripts\3_game\particles\particlelist.c` and points at a real `.ptc` under `P:\graphics\particles\`. Avoid `CAMP_STEAM_EXTINGUISH_START`: it registers the placeholder `default_01` (`particlelist.c:35`), not a steam effect.

"Stop it" means the effect keeps running until you stop it. Where the `.ptc` has no `Repeat` line, the evidence is that vanilla stops it explicitly.

| Device | Particle | Constant | Stop it? |
|---|---|---|---|
| Sprinkler | Water jet (weak) | `WATER_JET_WEAK` | Yes. Vanilla stops it with `StopParticle` (`P:\scripts\4_world\entities\building\underground\water\land_underground_waterreservoir.c:1168`) |
| Sprinkler alt | Water spilling | `WATER_SPILLING` | Yes. Vanilla stops it (`land_underground_waterreservoir.c:1132`) |
| Furnace | Generator smoke | `POWER_GENERATOR_SMOKE` | Yes. Vanilla destroys it with `SEffectManager.DestroyEffect` in `OnWorkStop` (`P:\scripts\4_world\entities\itembase\powergenerator.c:203`) |
| Furnace alt | Small camp smoke | `CAMP_SMALL_SMOKE` | Yes. Vanilla stops it with `StopParticle` (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1049`) |
| Overload | Barbed wire sparks | `BARBED_WIRE_SPARKS` | No. `Repeat 0`, deletes itself |
| Overload alt | Easter egg activate | `EASTER_EGG_ACTIVATE` | No. `Repeat 0`, deletes itself |
| Stove burner | Small stove fire | `CAMP_STOVE_FIRE` | Yes. `Repeat 1` |
| Steam vent | Smoking barrel steam | `SMOKING_BARREL_STEAM` | Yes. `Repeat 1` |
| Small steam vent | Smoking barrel steam (small) | `SMOKING_BARREL_STEAM_SMALL` | Yes. `Repeat 1` |
| Hot spring | Water vapor | `HOTPSRING_WATERVAPOR` | Yes. `Repeat 1` |
| Geyser | Geyser normal | `GEYSER_NORMAL` | Yes. `Repeat 1` |
| Menu evaporation | Main-menu evaporation | `EVAPORATION` | No. `Repeat 0`; vanilla plays it only in the menu |

Vanilla spells the hot spring constant `HOTPSRING_WATERVAPOR`; keep that spelling. The vanilla lines behind each row:

- `SMOKING_BARREL_STEAM` registers `smoking_barrel_steam` (`P:\scripts\3_game\particles\particlelist.c:203`), which loops (`Repeat 1` at `P:\graphics\particles\smoking_barrel_steam.ptc:47`).
- `SMOKING_BARREL_STEAM_SMALL` registers `smoking_barrel_steam_small` (`particlelist.c:204`), which loops (`Repeat 1` at `P:\graphics\particles\smoking_barrel_steam_small.ptc:49`).
- `CAMP_STOVE_FIRE` loops (`Repeat 1` at `P:\graphics\particles\fire_small_stove_01.ptc:51`).
- `HOTPSRING_WATERVAPOR` loops (`Repeat 1` at `P:\graphics\particles\hotspring_watervapor.ptc:107`).
- `GEYSER_NORMAL` loops (`Repeat 1` at `P:\graphics\particles\geyser_normal.ptc:31`).
- `BARBED_WIRE_SPARKS` is one-shot (`Repeat 0` at `P:\graphics\particles\electro_shortc2.ptc:51`).
- `EASTER_EGG_ACTIVATE` is one-shot (`Repeat 0` at `P:\graphics\particles\easter_egg_activate.ptc:53`).
- `EVAPORATION` is one-shot (`Repeat 0` at `P:\graphics\particles\menu_evaporation.ptc:41`) and vanilla uses it for `MenuEvaporation` (`P:\scripts\3_game\effects\effectparticle\menuevaporation.c:5`).
- `WATER_JET_WEAK` is stopped with `StopParticle` (`P:\scripts\4_world\entities\building\underground\water\land_underground_waterreservoir.c:1168`).
- `WATER_SPILLING` is stopped with `StopParticle` (`land_underground_waterreservoir.c:1132`).
- `CAMP_SMALL_SMOKE` is stopped with `StopParticle` (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1049`).

## Pattern E: Parameter tuning at runtime

Adjust particle properties after creation, for example smoke height from the room ceiling or spark intensity from overload severity. Vanilla tunes the fireplace's small smoke this way: `m_ParticleSmallSmoke.SetParameter(-1, EmitorParam.AIR_RESISTANCE, air_resistance)` (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1209`). The class extends `MyMod_DeviceBase` from Pattern A in `integration-patterns.md`.

```c
class MyMod_Chimney extends MyMod_DeviceBase
{
    protected Particle m_SmokeParticle;

    // Client: start the smoke and tune it for a low ceiling.
    protected void MyMod_StartLowSmoke()
    {
        vector smokePos = "0 0.5 0";
        MyMod_PlayParticle(m_SmokeParticle, ParticleList.CAMP_SMALL_SMOKE, smokePos);
        if (!m_SmokeParticle)
            return;

        // -1 = all emitters; more air resistance = shorter smoke column
        float airRes = 3.0;
        int emitterAll = -1;
        m_SmokeParticle.SetParameter(emitterAll, EmitorParam.AIR_RESISTANCE, airRes);

        // Scale particle size relative to the original .ptc values
        float sizeScale = 0.5;
        m_SmokeParticle.ScaleParticleParamFromOriginal(EmitorParam.SIZE, sizeScale);
    }

    override void EEDelete(EntityAI parent)
    {
        MyMod_StopParticle(m_SmokeParticle);
        super.EEDelete(parent);
    }
};
```

Since 1.30, vanilla vehicle effects do not retune a particle with separate `SetParameter` calls after playing it. They override `ParticleParamsOverride(ParticleParamsOverrideData)` on the effect class (`P:\scripts\3_game\effects\effectparticle.c:619`). Pattern E still works for a device; the vehicle form is in `dayz-1-30-particles.md`.

## Bringing older device code up to date

Mod device code written before 1.30 often uses the patterns in `integration-patterns.md` in a different form. Where it differs, keep the form below:

- Client check in the helpers. Older code tests `GetGame().IsDedicatedServer()`, which matched the vanilla fireplace up to 1.29 (1.29, not yet checked on `P:\`). Since 1.30 the fireplace `PlayParticle` helper tests `IsHeadlessOrDedicatedServer` (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1112`), and so does its `StopParticle` helper (`:1132`). Change both helpers to that check so a headless client skips the effect.
- `#ifndef SERVER` around client code. The define removes the code from a dedicated server build only. It does not skip a headless client, and in a test run where one diagnostic executable is both server and client it separates nothing (`SKILL.md`, pitfall 1). Keep the runtime check.
- One-shot sparks played with the legacy `Particle.PlayOnObject(sparkId, this, sparkPos)`. Pattern C uses the pool, `ParticleManager.GetInstance().PlayOnObject`, as vanilla barbed wire does. Both delete a non-looping particle for you.
- `SEffectManager.DestroyEffect(m_SmokeEffect)` that leaves the member as it is. Pattern D also sets the member to null, so the next start creates a fresh effect.
- A loop sound stopped with `m_LoopSound.SoundStop()` and then `m_LoopSound = null`. `StopSoundSet(m_LoopSound)`, used in the multi-effect cleanup template in `integration-patterns.md`, does both (`P:\scripts\3_game\entities\object.c:1314`).
- Particle choices. Replace `CAMP_STEAM_EXTINGUISH_START` used for a steam vent and `EVAPORATION` used as a looping effect. On `P:\` the first is the placeholder particle and the second is a one-shot, as the table in "Vanilla particles for placed devices" above shows. Use `SMOKING_BARREL_STEAM` for a vent, and pick another looping effect for anything that must keep running.
- A device with several looping effects cleans up in `EEDelete`, in the server path that switches it off, and in the destructor: the cleanup checklist in `integration-patterns.md`.
