# Materials and selections on a proxied car

Which two texture and movement diagnoses look solid but prove nothing, and why a selection the car's config drives must live in the parent model, never only in a proxy. The light selections of a car and their order are in `lights.md`.

## Two diagnoses that prove nothing on their own

### One `.rvmat` bound to two base textures

A material that resolves to two differently named `_co.paa` files looks like the cause of a texture defect. Hash the textures before acting on it: if the files are identical, reassigning the faces changes no pixel, and the defect lies elsewhere (the virtual file system at runtime, a material stage, or the UV layout against the atlas). A texture binding check is right to flag the split, but a fail there is not a diagnosis. Measured on a test helicopter whose two names held the same image.

### A part that moves with the vehicle on the server

A server measurement that shows the hull and its proxy moving together (a ratio of 1.000 over a climb, a constant separation) does not prove the client draws them that way. When a part "does not follow", measure both the server transform and what the client renders before designing a fix. A perfect server ratio with a visible mismatch points at rendering, replication or perception, and rules out the physics and the model's cohesion, which are the expensive branches to chase. Measured in game on a test helicopter.

## Selections the car drives belong in the shell

Any named selection the car's config drives must live in the parent model: `hiddenSelections` swapped with `SetObjectTexture` or `SetObjectMaterial` (`P:\scripts\3_game\entities\entityai.c:2884`), `model.cfg` animations declared on the parent, and `sections[]` entries. A selection that exists only inside a proxy model is not reached.

Measured in game on a test car with its interior as a proxy:

- Dashboard needle animations declared over the interior proxy stayed still.
- The selections that worked, the dashboard light at index 8 and a navigation screen at index 9, had their faces in the shell.
- A static proxy animates none of its pieces. Moving the needles off the proxy left the steering wheel animation on it, and the wheel had never turned either.

When one dead animation shows a static proxy, list every `Animations` class bound to that proxy and move them all to the shell in the same change, with their bones added to the shell skeleton.

## Moving selections out of a proxy

1. Every `hiddenSelections` entry needs its faces in the shell, in LOD 0 and in the View Pilot LOD (resolution 1100, which mirrors LOD 0).
2. Move the faces out of the proxy rather than copying them when the selection can wear a different material from the base. A swap on the shell copy z-fights the proxy copy. A duplicate is safe only while both copies always share one material.
3. Copy vertex order and stored normals exactly when moving. Faces that render correctly from the proxy then render correctly from the shell.
4. Check the move as you make it: the component picked by aspect and centre, the face count change per LOD, the size of each selection, and proxies and bones left untouched.
5. Scan the body against the proxy for faces that coincide and keep one copy of each. On a test car, a scan at 0.05 mm tolerance found 384 dashboard faces in the body lying exactly on proxy faces with a different material, and 42 proxy panel faces 0.5 mm behind the dashboard light; the dashboard flickered at rest.

## One writer for the dashboard light

Vanilla registers index 8, `SELECTION_ID_DASHBOARD_LIGHT` (`P:\scripts\4_world\entities\vehicles\carscript.c:182`), for both `DashboardOn` with `dashboardMatOn` and `DashboardOff` with `dashboardMatOff` (`carscript.c:230` and `:231`). `UpdateLightsServer` (`carscript.c:1974`) sets `DashboardOn` when `LightIsOn()` is true (`:1993`) and `DashboardOff` whenever it is false (`:2022`) each time it runs, which includes braking, gear changes and each sync.

A script that must set the dashboard material again after a sync goes through that same method. A timer that writes a fixed `dashboardMatOn` fights it, and the index flickers between the two materials (measured in game).
