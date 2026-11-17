# Materials and selections: two misleading diagnostics

Two diagnoses that look solid and are not (one material on two identical textures, and a part that follows on the server but not on screen), and the rule that a selection the car's config drives must live in the parent model, never only in a proxy.

> Status: field notes measured on third-party mods (LFHeli OH-1, SUB_BRZ, MercedesAMGLF), each named in its entry. Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. The `carscript.c` numbers in this file were opened and match this repo's `P:\` (a 1.30 build). Tags such as SP-205 or LL-464 are the notes' own lesson numbers, and `[EXACT]`, `[DESIGN]` and `[CLAIM-...]` are the notes' own evidence labels. Paths such as `<vehicle-import>\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. The light selections of a car and their order are in `lights.md`.

## Vanilla anchors checked on `P:\`

- `SELECTION_ID_DASHBOARD_LIGHT` is 8: `P:\scripts\4_world\entities\vehicles\carscript.c:182`.
- `dashboardMatOn` is registered on the `DashboardOn` selection: `P:\scripts\4_world\entities\vehicles\carscript.c:230`.
- `UpdateLightsServer` rewrites the light selections: `P:\scripts\4_world\entities\vehicles\carscript.c:1974`.
- `SetObjectMaterial` is declared at `P:\scripts\3_game\entities\entityai.c:2884`.

## How these lessons are ordered

These lessons were split out of the source skill body on 2026-08-15. The reference
tables of `skills/dayz-vehicles/SKILL.md` say when to read this file.
Nothing in this file is repealed: these are active lessons, ordered by topic
instead of date.

---

## Two diagnoses that look solid and are not: identical textures, and server co-move (SP-094, added 2026-07-26)

Both cost real cycles on LFHeli OH-1. Both are one cheap measurement away.

**A. "One .rvmat bound to two base textures" is NOT automatically the cause of a texture defect.**
On OH-1, `oh1_fuselage.rvmat` resolved to `rd_oh1_fuselage_co.paa` (10403 faces) and
`rd_oh1_hs_fuselage_basecolor_co.paa` (6420 faces), UVs perfectly inside [0,1]. It reads like a
smoking gun. **Hashing the files killed it**: all four .paa were byte-identical
(`16B0FD978AAD7552...`, 6822200 bytes) - the same image under two names, so reassigning the faces
would not change a single pixel. Rule: before concluding a texture-binding split explains anything
visible, **hash the referenced textures**. If they are identical, the split is hygiene, not a cause,
and the real defect is elsewhere (runtime/VFS, material stage, UV layout vs atlas content).
This applies directly to the T1 rule of `texture_binding_gate.py` - the gate is right to flag it,
but a FAIL there is not a diagnosis.

**B. Server-authoritative co-movement does NOT prove the client renders it that way.**
The user reported the hull staying behind while rotors and interior climbed. The instrumented
measurement over a 28 m ascent said the opposite: `ratio shell/root = 1.000`, `proxy/root = 1.000`,
separation constant at 0.626 m - hull and proxy co-move exactly. Both statements were true: the
authoritative transform is coherent and the client still renders the part detached. Rule: when a
part "does not follow", measure BOTH sides before designing a fix. A perfect server-side ratio with
a visible mismatch points at render/replication/perception, and it rules out the physics and
cohesion branches - which is worth a lot, because those are the expensive ones to chase.

## Parent-driven selections (hiddenSelections / config anims) do NOT reach a PROXY - host them in the SHELL (SP-192, added 2026-08-07, SUB_BRZ + LFVehicleUI)

Any named selection the CAR's config must drive - hiddenSelections swaps
(SetObjectTexture/SetObjectMaterial), model.cfg Animations declared on the parent,
sections[] entries - must live in the PARENT model, never only inside a proxy sub-p3d.
Evidence, both measured on SUB_BRZ: (a) dashboard needle anims declared over the interior
proxy = needles STATIC in-game (s45 falsification); (b) the selections that DO work
(light_dashboard idx 8; screen_nav idx 9 for the nav screen) are faces hosted in the shell
- light_dashboard ships duplicated shell+proxy with identical coords and works FROM the
shell copy. MercedesAMGLF carries the same latent defect (interior selections in proxy).

A static proxy animates NONE of its pieces, and one dead anim hides the rest (SP-407, added 2026-10-01, SUB_BRZ s95->s96). [DESIGN] s95 moved the needles off the interior proxy and left `DrivingWheel` on it - the steering wheel had never turned, and finding it cost another full cycle. When a dead animation exposes a static proxy, enumerate EVERY `Animations` class bound to that proxy and move them ALL to the shell in the SAME change, with their bones appended to the shell skeleton.

Rules for a proxy-split car (day-1 for car #2, surgery for cars in flight):
1. Every hiddenSelections entry needs its faces in the SHELL, in LOD0 AND the ViewPilot
   1100 (SP-189: 1100 mirrors LOD0 content).
2. MOVE the faces out of the proxy instead of duplicating when the selection can carry a
   DIFFERENT material than the base (a swap on the shell copy z-fights the proxy copy).
   A duplicate is only tolerable while both copies always share the same material - the
   light_dashboard duplicate is a latent z-fight for the dashboard-light swap.
3. Copy vertex order and stored normals VERBATIM when moving (SP-190/191): faces that
   render correctly from the proxy keep rendering correctly from the shell (empirical
   control: the instrument cluster).
4. Reference surgery with asserts (component pick by aspect+centre, per-LOD face deltas,
   selection cardinality, proxies/bones untouched):
   <vehicle-import>/work/lfvui_f2/surgery_screen_nav.py.
5. Scan body-vs-proxy for COINCIDENT faces and keep ONE copy (SP-401, added 2026-10-01, SUB_BRZ
   s94): a vertex-match scan (0.05 mm tolerance, negative control) found 384 `light_dashboard_static`
   body faces sitting exactly on proxy faces wearing a DIFFERENT material, plus 42 proxy panel faces
   0.5 mm behind `light_dashboard` - the user saw intermittent flicker at rest. Coincident duplicates
   that can ever wear different materials z-fight; leave one owner per face.
6. The dashboard light index has ONE writer (SP-401). [EXACT][CLAIM-DASHBOARD-LIGHT-RESYNC] Vanilla
   registers `SELECTION_ID_DASHBOARD_LIGHT` (index 8) with `dashboardMatOn`/`dashboardMatOff`
   (`carscript.c:230-231`) and `UpdateLightsServer` rewrites it on every resync - `DashboardOff`
   whenever `!LightIsOn()` (`carscript.c:1974-2025`, called on braking, gear change and each sync;
   DayZ 1.30.164014 Exp). Any script that must re-assert the dashboard material after a resync calls
   that same owner; a timer writing a fixed `dashboardMatOn` fights the resync path and the index
   flickers between the two materials (measured in game).
