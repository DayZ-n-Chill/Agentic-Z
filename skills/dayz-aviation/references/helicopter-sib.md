# SIB helicopter: recovered kinematic model

How the SIB helicopter mod (lfbanov / sibnic, Workshop `3485438937`, "La Frontera" / Fortune Mods, author `SIBNIC`, internal `ver=8.041`) flies a `CarScript` child: class layout, its simple `SetVelocity` flight loop, the JSON coefficient store, inputs and actions, rotor animation, damage zones, and what was not recovered. Open it when a task needs a second, simpler kinematic example next to `helicopter-rffs.md`, or when it touches collective, cyclic, anti-torque, rotor animation, engine start and stop, the altitude ceiling or helicopter damage zones.

Third-party material, not yet checked on `P:\`. The mod ships obfuscated. Its two script PBOs (`HelicopterMod_lfbanov_SERVER_v8.041.pbo` and `HelicopterSIB_Scripts_lfbanov.pbo`) were recovered on 2026-07-07 and the recovered files were read; those files are not in this repo. Citations are `file:line` into the recovered copies, named as the recovery left them (`SERVER\unknown_16894.c`, `CLIENT\unknown_15761.c`). Tags: `[RECOVERED]` read from the recovered source, `[INFERRED]` reasoned from it, `[UNVERIFIED]` not recovered, so do not invent it, `[DESIGN]` yours to design.

Unlike the fixed-wing notes, this is a real rotary-wing flight model read from source, not a community guess. Two limits apply (see the last sections): the advanced variant's core integrator did not survive recovery, and the whole model is a homegrown kinematic hack, not a physically modelled rotor. Learn the pattern from it and write the mod's own code; `skills/_shared/vehicles/helicopters.md` says which model to build from.

---

## 1. Architecture — `HeliTest_SIB : Heli_sib_cript : CarScript`

[RECOVERED] The same `CarScript` as aircraft base that `fixed-wing-lm-planes.md` documents for planes, but three layers deep
(`CLIENT\unknown_15761.c`):

| Layer | Adds | Cite |
|---|---|---|
| `CarScript` (vanilla) | wheels, seats, fuel, damage, sound | — |
| `Heli_sib_cript : CarScript` | full `SimulationModule` (Axles/Wheels — 4 wheels for a ground-taxi fallback), `Crew{Driver,CoDriver}`, car-style `AnimationSources` (`DoorsDriver`, `HideDestroyed_*`, `AnimHitWheel_*`), electrical/fuel stubs (`fuelCapacity=50`, `electricConsumptionIgnition=3001`) | `:117-287` |
| `HeliTest_SIB : Heli_sib_cript` | rotor + flight `AnimationSources` (`hide_rotor`, `hide_start`, `rot_h_start/blur_end`, `rot2_h_*`, `toplivo`, dial detectors), `Crew` expands to Driver+CoDriver+Cargo1+Cargo2, heli `DamageZones` (Body/Chassis/Engine/Fuel/Rotor1/Rotor2/Proj), `Cargo`, `ObstacleGenerator` | `:288-710` |

**Key point:** the flight model is entirely in **script overriding a ground vehicle** — the config
still declares wheels, axles, steering, gearbox (`drive="DRIVE_AWD"`, `class Engine{torqueMax=114;…}`,
`:315-420`). Those are the CarScript ground fallback; the heli overrides `EOnSimulate` and drives
itself with `SetVelocity` / `SetOrientation` (simple model) or `dBodyApplyForce/Torque` (advanced).

Size variants are pure `Cargo`-size subclasses of `HeliTest_SIB`:
`HeliSIB_big/middle/little/minimal/none` (`:711-755`).

---

## 2. Flight model — the two variants

The mod ships **two flight models under the same class name**. Document both; **build from the
simple one** (the advanced one is license-gated and its core did not survive recovery).

### 2a. Simple model — kinematic, `SetVelocity`-based [RECOVERED, fully legible]

File `SERVER\unknown_16894.c` (client copy `CLIENT\unknown_16894.c` is identical through the class
body). Not license-gated. This is the teachable pattern.

**Coefficients** (defaults in the class body; overwritten at runtime from JSON via `go_conf()`):

| Field | Default | Role | Cite |
|---|---|---|---|
| `c_startDurationInv` | `0.05` | engine spin-up inverse duration | `:26` |
| `c_liftForceCoef` | `3.0` | lift/collective strength | `:27` |
| `c_altNoForce` | `500.0` | altitude (m) at which lift → 0 (hard ceiling) | `:28` |
| `c_altFullForce` | `450.0` | altitude (m) below which lift is full | `:29` |
| `c_cyclicAsideForceCoef` | `1.3` | sideways (roll→translate) strength | `:30` |
| `c_cyclicForwardForceCoef` | `1.0` | forward (pitch→translate) strength | `:31` |
| `c_bodyFrictionCoef` | `0.3` | body friction | `:32` |
| `c_heliMass` | `1500.81` | mass | `:33` |

> Note: in the *simple* model these `c_cyclic*` / `c_altFullForce` / `c_bodyFrictionCoef` /
> `c_heliMass` fields are **loaded but the simple `Simulate()` does not actually read most of them**
> — the simple integrator is hand-tuned with literals (see below). They are the config *contract*
> the advanced model consumes. [INFERRED] from reading `Simulate()`.

**Control loop** — `EOnSimulate` (server only) reads two animation phases as the state gate, then
runs input + integration (`:425-452`):

```c
// EOnSimulate: gate on engine (hide_start) AND rotor (hide_rotor) both == 1.0
anim_rotor  = GetAnimationPhase("hide_rotor");
anim_engine = GetAnimationPhase("hide_start");
KeyboardPilot(dt, anim_engine, anim_rotor);   // read inputs -> m_RollKey/m_PitchKey/m_Yaw/m_rotorTurn
Simulate(dt, anim_engine, anim_rotor);         // integrate
```

[RECOVERED] **Inputs** (`KeyboardPilot`, `:124-201`) read via
`playerObj.GetInputInterface().SyncedValue("UASIBHeli<X>")`, each a boolean `>=0.5`:

| Input | Effect on state | Meaning |
|---|---|---|
| `UASIBHeliCyclicRight` / `…Left` | `m_RollKey ∓ 0.6` | roll (cyclic aside) |
| `UASIBHeliBack` / `…Forward` | `m_PitchKey ∓ 0.6` | pitch (cyclic fore/aft) |
| `UASIBHeliLeft` / `…Right` | `m_Yaw ± 0.6` | yaw (anti-torque / pedals) |
| `UASIBHeliUp` / `…Down` | `m_rotorTurn = ±2.8` | collective (climb/descend) |

[RECOVERED] **Integration** (`Simulate`, `:298-391`):

1. **Ground/ceiling probe**: `m_height = Distance(GetPosition, SurfaceY-projected pos)` (`:300-303`).
   Above `1500` m it force-hides rotor/engine (kill switch, `:319`). At `5..6` m it zeroes angular
   velocity (`dBodySetAngularVelocity(this,"0 0 0")`, landing settle, `:326-329`).
2. **Death**: if `GetHealth("","") <= 0` → hide rotor/engine, `m_isDead=true`, `SetSynchDirty()`,
   error-anim the rotors (`:306-315`).
3. **Attitude → forward speed** (`HeliPitch`, `:204-221`): reads `GetOrientation()[1]` (pitch);
   nose-down (`< -5`) accelerates `m_heliSpeed` (cap `60`), nose-up (`> 5`) decelerates (floor `-10`).
   **Forward motion is a side effect of pitch attitude, not a direct thrust vector.**
4. **Bank → yaw** (`HeliRoll`, `:224-258`): reads `GetOrientation()[2]` (roll); banking turns the heli
   (`m_Yaw`), harder bank (>59°) triggers an auto-descend (`m_rotorTurn=-3.0`). Applies the yaw to
   orientation directly with `SetOrientation`.
5. **Auto-leveling** (`AutoAlignment`, `:262-292`): if the pilot isn't actively rolling/pitching
   (`m_RollKey==0`/`m_PitchKey==0`), nudge attitude back toward level (±0.1 per tick past a ±3° dead
   zone). **This is the mod's "auto-stabilization" — a simple attitude-recenter, not a PID.**
6. **Apply attitude**: rotate `GetOrientation()` by `Math.RAD2DEG * m_{Roll,Pitch,Yaw}Key * dt`, then
   `SetOrientation` (`:349-353`).
7. **Apply velocity** (`:360-387`): build a world velocity vector —
   - Forward: `sin/cos(heading) * m_heliSpeed` into X/Z (`:365-371`).
   - Vertical: `m_rotorTurn` (collective) into Y; **with no collective input a constant
     `+0.25` m/s up is applied** (`:384`) — this is the passive hover-lift term, the closest thing to
     "lift(collective)" in the simple model.
   - `SetVelocity(this, m_Velocity)` (`:387`). **Velocity is set, not force-applied** → arcade feel,
     no momentum/inertia carryover between ticks.

[INFERRED] **There is no true collective→lift force curve in the simple model.** "Lift" = a fixed
`+0.25` m/s baseline plus `m_rotorTurn` (±2.8) when climbing/descending. The `c_altNoForce=500` /
`c_altFullForce=450` ceiling coefficients are declared but **the height clamp is a hard literal
`1500` in `Simulate`**, not those coefficients — so in the simple model the documented altitude
ceiling is effectively unused. [UNVERIFIED] whether the advanced model wires the 450/500 band.

### 2b. Advanced model — force/torque, autopilot, license-gated [RECOVERED but incomplete]

Files `SERVER\unknown_16458.c` / `CLIENT\unknown_18705.c` + `SERVER\unknown_10783.c`. Every method is
identifier-mangled and every entry point is guarded by `license_active_helisib` (a runtime license
check that GETs `sibnic.info/sib/mod13.php`, `SERVER\unknown_10783.c:319-395`).

What is recoverable:

- **Force-based physics**: the only recovered `dBodyApplyForce` / `dBodyApplyTorque` calls are in the
  helper `qmdkldkpqpmlsib(...)` (`SERVER\unknown_10783.c:454-455`): it computes a target-velocity
  delta × `dBodyGetMass(...)` and applies it as a body force, plus a torque term — i.e. proper rigid-
  body forcing, unlike the simple model's `SetVelocity`. It uses model-space transforms
  (`Transform_SIB`, `unknown_18705.c:4-28` matrix helpers) to convert local up/forward into world.
- **Autopilot state machine**: enum `AutopilotState_SIB { Far, Brake, Near, Align, Reached }` +
  `StopMode_SIB { SMNone, SMLand, SMGetIn, SMGetOut }` (`CLIENT\unknown_18705.c:33-51`) with
  `m_state`/`m_stopMode` fields and a large `get_botmap_*`/`set_botmap_*` accessor surface
  (`:232-270`). This is a genuine autohover/auto-navigate ("bot map") system.
- **Contact-cache damage** (`vlgvxpruyfuxogsib` / `hymidyeqrrwulesib`): per-zone impulse accumulation
  → `ProcessDirectDamage(DT_CUSTOM,…)` with per-zone coefficients + crew-injury lerp
  (`unknown_16458.c:244-333`, `unknown_18705.c:313-402`).

What is **not recoverable** — do not fabricate: the central integrator **`hkdxkhzidmpsib(dt,this)`**
(dispatched from `EOnSimulate`, `unknown_16458.c:216`; client twin `zcggxjtfzrsib`,
`unknown_18705.c:285`) has **no definition in any recovered file**. The lift-vs-altitude curve, the
collective→force mapping, and how `c_altFullForce`/`c_altNoForce` gate lift all live inside that
missing function. [UNVERIFIED]. **This was confirmed exhaustively** (2026-07-07, 2nd pass): every
non-junk block of both PBOs was decompressed with a relaxed extractor (9,546 server + 13,968 client
entries) — `hkdxkhzidmpsib` appears **only** as the license-gated call, never as a definition. Its
body is not shipped in plaintext in these two PBOs (it is the most heavily protected part of the paid
mod). The recoverable force anchor is the low-level applicator `qmdkldkpqpmlsib` (see the takeaway at the end), not the
integrator that feeds it.

---

## 3. Config store — JSON-in-`$profile`, positional coeff map

[RECOVERED] The flight coefficients are **not in config.cpp**. They live in a per-class JSON file
loaded at mission init into a global `map<string,float>`:

- Store: `ref map<string,float> ssaBWDQnlAkkAQpglobal = new map<string,float>;`
  (`CLIENT\unknown_1929.c:4`; referenced everywhere as `ssaBWDQnlAkkAQp`).
- File: `$profile:\Heli_sib\<classname>_config.json`, auto-created from defaults if missing, then
  loaded, via `JsonFileLoaderVert<T>` (`CLIENT\unknown_6344.c:66-97`).
- Default struct: `class Json_Heli_MH6` (`CLIENT\unknown_6344.c:2-53`) with **legible field names +
  defaults**: `Lift_power=3.3`, `No_power=1200`, `Full_power=1250`, `side_strength=1.3`,
  `power_before=1.0`, `friction=0.3`, `Mass=1400.81`, `incline/front_tilt=0.9`, `m_povorot=0.4`,
  per-zone damage bools, `maxFuel=70`, `gasoline_costs=0.0004`, sound volumes, `coef_damage_weapon`,
  `auto_off_autopilot`, `auto_engine_shutdown`, etc.
- Load is **positional**: `vert_conf_MH6` does `ssaBWDQnlAkkAQp.Insert(child_name+"_"+num_mass, …)`
  incrementing `num_mass` (`unknown_6344.c:105-154`); the class reads them back in the **exact same
  order** in `go_conf()` (`unknown_16894.c:475-515`) / `pxmcpzlfyvhxsib()`
  (`unknown_16458.c:337-393`). So the JSON→coeff mapping is index-by-index:

| JSON field (`Json_Heli_MH6`) | Simple-model field (`go_conf`) |
|---|---|
| `duration` | `c_startDurationInv` |
| `Lift_power` | `c_liftForceCoef` |
| `No_power` | `c_altNoForce` |
| `Full_power` | `c_altFullForce` |
| `side_strength` | `c_cyclicAsideForceCoef` |
| `power_before` | `c_cyclicForwardForceCoef` |
| `friction` | `c_bodyFrictionCoef` |
| `Mass` | `c_heliMass` |
| `incline`/`front_tilt`/`inclineMouse`/`front_tiltMouse`/`m_povorot` | `m_naklon`/`m_nabor`/`m_naklonMouse`/`m_naborMouse`/`m_povorot` |
| `Chassis`/`Body`/`Engine`/`Fuel`/`Rotor1`/`Rotor2` | `b_Chassis`/`b_Body`/`b_Engine`/`b_Fuel`/`b_Rotor1`/`b_Rotor2` (damage-zone enable bools) |

[INFERRED] The `MH6` suffix (`Json_Heli_MH6`, `vert_conf_MH6`) suggests a per-model config family
(an MH-6 Little Bird variant); `vert_conf` dispatches by `child_name.Contains("HeliMH6_SIB")`
(`unknown_6344.c:57-64`) — other models would provide their own `Json_Heli_*` + `vert_conf_*`.

---

## 4. Inputs & actions

[RECOVERED]

- **Flight inputs** are custom `UASIBHeli*` UA actions (see §2a table) declared in `modded_Inputs.xml`
  (`inputs = "HelicopterModScripts/modded_Inputs.xml"`, `unknown_15761.c:21`) and registered
  client-side via `GetUApi().GetInputByName("UASIBHeliEngine_new" / "UASIBHeliAutopilot" /
  "UASIBHeliHide")` (`CLIENT\unknown_18863.c:121,188,255`). [UNVERIFIED] the `.xml` itself — not
  recovered (binary XML in the PBO); the input *names* are confirmed from the script reads.
- **In-vehicle continuous actions**: `DefaultActionInputHelicopterEngine` → `UASIBHeliEngine_new`,
  `DefaultActionInputHelicopterHide` → `UASIBHeliHide` (`SERVER\unknown_294.c` / `unknown_286.c`;
  both `ContinuousDefaultActionInput`, `m_DetectFromTarget=false`).
- **Engine start/stop** actions: `ActionHeliStartEngineSIB` / `ActionHeliStopEngineSIB` (simple,
  `unknown_16894.c:609/645`) and mouse/keyboard variants `Action_Helicopter_Start_Engine_*` /
  `Stop_Engine_*` (advanced, `unknown_10783.c:39-228`). Start sets `hide_start=1.0` +
  `heli.OnEngineStart()`; stop sets `hide_start=0`/`hide_rotor=0`, zeroes rotor-speed-wanted,
  error-stops the blur anims, `heli.OnEngineStop()`.
- **Autopilot / cockpit-button actions** raycast a memory point: `GetMemoryPointPos("avtopilot")` /
  `("button_beam")` then `ModelToWorld` + distance-gate the player
  (`CLIENT\unknown_2491.c`, `unknown_2306.c`). Pattern: cockpit buttons are memory points you must
  be within range of.

---

## 5. Rotor animation & engine start sequence

[RECOVERED] Rotors are driven by **`SetAnimationPhase` on paired anim sources**, not by RPM:

- Anim sources (config `unknown_15761.c:455-514`): `hide_rotor`, `hide_start`, `rot_h_start` /
  `rot_h_blur_end` (rotor 1), `rot2_h_start` / `rot2_h_blur_end` (rotor 2), plus `toplivo` (fuel) and
  a bank of dial detectors (`HorizonBankdetect`, `visotadetect`, `rpmdetect`, `speed`, …).
- **Blur swap**: a static (`rot_h_start`) and a spinning-blur (`rot_h_blur_end`) mesh are cross-faded
  by health-gated helpers `animatezzstart` (spinning: start=1, blur=0) / `animatezzstop` (stopped:
  start=0, blur=1) — only if `GetHealth01("Rotor1"/"Rotor2") > 0.15`
  (`unknown_16894.c:526-595`). Dead rotors get `animatezzerror1/2` (freeze).
- **Engine-start sequence** (`SERVER\unknown_12270.c:7-25`, RPC `HelicopterStartSimulate`): when
  `hide_start==1.0` → `SetAnimationPhase("hide_rotor",1)`, `animatezzstart(heli)`, `rot_start(heli)`,
  `mainRotor(heli)`. `rot_start` (`unknown_5972.c:258`) sets the rotor-speed-wanted field (spin-up).
- **Fuel**: anim source `toplivo` doubles as the fuel gauge; `ConsumeFuel()` decrements it every 5 s
  by `z_zatrat + (fuel-damage/4)` (`unknown_16894.c:454-472`).

[INFERRED] Rotors are baked geometry with a blur variant here (not attachable items) — contrast with
the *other* community heli (`HelicopterSIB_Hommade_LF`) described at the end of
`helicopter-model-comparison.md`, where blades were inventory attachments. Different mod, different choice.

---

## 6. Engine start/stop, fuel, damage zones

[RECOVERED]

- **Damage zones** (`unknown_15761.c:580-684`): `Body`, `Chassis`, `Engine`, `Fuel`, `Rotor1`,
  `Rotor2`, `Proj` — each with `memoryPoints[]={"dmgzone_*"}`, own hitpoints (Body 6000, Chassis/
  Engine 3000, Rotor1/2 2000, Fuel/Proj 700), `transferToGlobalCoef` near-0 (zones don't bleed into
  global health except Body's 0.001). Global `hitpoints=1000`.
- **Per-zone enable bools** `b_Chassis/b_Body/b_Engine/b_Fuel/b_Rotor1/b_Rotor2` come from the JSON;
  **if all six are 0 → `SetAllowDamage(false)`** (invulnerable heli, `unknown_16894.c:500-503`).
- **Contact damage** (simple `OnContact`, `unknown_16894.c:400-421`): `dmg = Impulse *
  m_dmgContactCoef`; a hard hit (`vel>10 || angVel>5 || Impulse>1000`) also subtracts the whole zone
  health (destroys the zone).
- **Weapon damage** gate (`SERVER\unknown_3380.c`): `EEOnDamageCalculated` returns false (no damage)
  when `coef_damage_weapon==0`; `EEHitBy` scales incoming damage by `coef_damage_weapon`
  (add-back if `<1`, extra if `>1`). Blades (`SIB_blade`) and doors (`Sib_heliDoor`) proxy to their
  parent heli's coefficient.
- **Transport-hit impulse** (`unknown_10783.c:118-146`): overrides `DayZPlayerImplement.
  RegisterTransportHit` — a destroyed heli hitting the player applies `dBodyApplyImpulse`.

---

## 7. Client/server split & the license gate

[RECOVERED]

- Both flight models are `modded class HeliTest_SIB` present in **both** `SERVER\` and `CLIENT\`
  (`unknown_16894.c` on both; advanced `unknown_16458.c` server / `unknown_18705.c` client). The
  physics run **server-authoritative**: `EOnSimulate` bodies are gated `if (GetGame().IsServer())`
  (`unknown_16894.c:428`; advanced additionally `&& license_active_helisib`,
  `unknown_16458.c:214`).
- The advanced model's `license_active_helisib` flag is set true only after a successful HTTP GET to
  `sibnic.info` returning a signed config (`unknown_10783.c:319-395`). **When authoring your own heli,
  drop the whole license layer** — it is DRM specific to this author, not part of the flight pattern.

---

## 8. Not recovered / [UNVERIFIED] — do not fabricate

- **`config.bin`** was not decompiled; the config used here is the *script* config
  (`unknown_15761.c`). A real deployed heli would also have a binarized `config.bin`; assume the
  script config is authoritative for classes/inheritance but **verify any exact numeric against the
  live mod** before shipping.
- **`model.cfg`** (skeleton bones, the real rotor/wheel animation `class Animation` sources bound to
  the `.p3d` selections) — not recovered. The AnimationSources *names* are known (from config); the
  model.cfg bone graph is [UNVERIFIED].
- **The `.p3d` memory points** — inferred from script reads (`dmgzone_body/chassis/engine/fuel/
  rotor1/rotor2/proj`, `avtopilot`, `button_beam`, crew `pos_*` / proxy `crew*`) but the actual model
  is not present. [UNVERIFIED] the full memory-point set.
- **The advanced integrator `hkdxkhzidmpsib`** (the true lift/collective/altitude curve) — referenced,
  definition missing. The lift-vs-altitude force law is [UNVERIFIED]. A 2nd exhaustive pass (all
  23,514 non-junk blocks across both PBOs re-decompressed with a patched extractor) confirmed the
  body is not present in plaintext (the search script stayed with the research copies and is not in
  this repo).
- **`modded_Inputs.xml`** — input names confirmed from script; the XML bindings/defaults not
  recovered.

## Takeaway for building your own heli

Buildable today from RECOVERED material: the class chain (`HeliTest_SIB : Heli_sib_cript :
CarScript`), the `AnimationSources`/`DamageZones`/`Crew` config, the input set + engine-start/stop
actions, the rotor blur-swap animation, and the **simple kinematic flight loop** (`KeyboardPilot` +
`Simulate` with `SetVelocity`/`SetOrientation`). That is a complete, self-contained flyable heli.

Do not reach for the advanced force-based model — its core is missing and it's license-locked. If you
want true `dBodyApplyForce` rotor physics, treat `qmdkldkpqpmlsib` (`unknown_10783.c:454`) as the only
recovered anchor and design the lift curve yourself (mark it `[DESIGN]`).
