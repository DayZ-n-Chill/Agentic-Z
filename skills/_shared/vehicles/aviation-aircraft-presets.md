# Aircraft parameter presets

Which aircraft LM_Planes builds on one base class, and the parameter values it uses for a large plane, a small plane, an aerobatic plane and a flying car, as starting points for a new aircraft.

The values are LM_Planes's own (Workshop `3730564764`), read from its scripts; they are mod tuning, not vanilla, and not checked in game here. The functions they override are described in `aviation-aerodynamics.md`. The one vanilla anchor is the base the mod builds on: every aircraft is a `CarScript` (`P:\scripts\4_world\entities\vehicles\carscript.c:94`).

## The LM_Planes fleet

| Aircraft | Variants | Floats | Crew | Weapons |
|---|---|---|---|---|
| Tigermoth | MK1; MK2 (sport, no top wing); MK3 (seaplane) | MK3 only | 2, driver and co-driver | None |
| Cessna180 | Base only | No | 2 | None |
| Catalina | Base | Yes, flying boat | 5, driver, co-driver and three cargo seats | A visible Browning M2 .50 cal |
| Spitfire | MK1 only | No | 1 | Yes, `LM_Planes_Tracer` |
| DC-3 | Base, twin engine | No | 2 | None |
| StuntPlane | Base | No | 2 | None |
| Z37_Bumblebee | Base, crop sprayer | No | 2 | None |
| Patty_Wagon | A car that flies | Yes, amphibious | 2 | A car horn |

The weapons are covered in `aviation-weapons.md` and the floating in `aviation-seaplanes.md`.

## Large aircraft

The Catalina and the DC-3 share these exact values:

```c
override protected float GetWingArea()           { return 28.0; }
override protected float GetWingSpan()           { return 14.5; }
override protected float GetWingAR()             { return 7.5; }
override protected float GetWingMeanChord()      { return 1.93; }
override protected float GetEngineMaxPower()     { return 5200.0; }
override protected float GetPropEfficiency()     { return 0.88; }
override protected float GetEngineSpoolUp()      { return 7.0; }   // slow spool, more inertia
override protected float GetEngineSpoolDown()    { return 3.5; }
override protected float GetElevatorAuthority()  { return 0.85; }  // more authority to move the mass
override protected float GetAileronAuthority()   { return 0.70; }
override protected float GetRudderAuthority()    { return 0.95; }
override protected float GetMaxSpeedMs()         { return 72.0; }
override protected float GetCameraDistance()     { return 28.0; }  // wider orbit
override protected vector GetCameraOffset()      { return "0 5.5 0"; }
override protected float GetStallBaseSpeedKmph() { return 50.0; }  // the large wing stalls later
```

## Small aircraft

The Tigermoth values, the same for the Cessna180, StuntPlane and Z37:

```c
override protected float GetWingArea()           { return 22.0; }
override protected float GetWingSpan()           { return 8.9; }
override protected float GetWingAR()             { return 5.2; }
override protected float GetWingMeanChord()      { return 1.7; }
override protected float GetEngineMaxPower()     { return 3100.0; } // about 3000 to 4000 across the small planes
override protected float GetPropEfficiency()     { return 0.92; }
override protected float GetEngineSpoolUp()      { return 2.8; }    // fast spool
override protected float GetElevatorAuthority()  { return 0.60; }
override protected float GetMaxSpeedMs()         { return 52.0; }
override protected float GetCameraDistance()     { return 14.0; }
override protected vector GetCameraOffset()      { return "0 2.8 0"; }
override protected float GetStallBaseSpeedKmph() { return 62.0; }
```

## Aerobatic tuning

The StuntPlane is the small airframe with sharper overrides:

```c
override protected float GetAileronEffectiveness() { return 0.87; }  // 74 percent over the default 0.50
override protected float GetAileronAuthority()     { return 1.20; }  // the highest in the mod
override protected float GetStallBaseSpeedKmph()   { return 18.0; }  // very low, for stunts
override protected float GetMinFlightSpeedKmph()   { return 32.0; }
override protected float GetMaxSpeedMs()           { return 95.0; }  // the fastest in the mod
override protected float GetLevelFlightSpeedKmph() { return 250.0; }
override protected bool  HasRetractableGear()      { return false; }
```

## Flying car tuning

The Patty Wagon is a Tigermoth chassis built to drive and only just fly:

```c
override protected float GetEngineMaxPower()     { return 3200.0; }
override protected float GetStallBaseSpeedKmph() { return 18.0; }  // lifts off if pushed hard enough
override protected float GetMinFlightSpeedKmph() { return 32.0; }
override protected vector GetCameraOffset()      { return "0 2.5 0"; }
```

It adds the small water template from `aviation-seaplanes.md` to drive on water.
