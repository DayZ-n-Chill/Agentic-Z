# Rip wheels, doors and interior

How to deploy a rebuilt visual shell without losing the structural LODs, make wheels draw and use the car's original rim, change the track width, take doors from the rip's pre-cut parts, and give first person the car's own interior.

Measured in game and offline on cars built from rips (`rip-import.md`), against the vanilla sedan and a working test quad. The sedan's models are binarized, so frames and counts read from them came from converted copies (**model knowledge**).

## Deploying a rebuilt shell

A rebuilt shell holds only the visual LOD, while the deployed shell holds the structural LODs (Geometry, Memory, LandContact on older builds, View Geometry and Fire Geometry with crew proxies, components and hubs) that make spawning and get-in work. Deploying the rebuilt file whole destroys both. Transplant instead: the rebuilt visual LOD 0 plus the deployed shell's other LODs, which share the same car space. Back up first, and check the result: the expected LOD count, every proxy reference, the structural selections, and a body of more than 1000 faces.

The transplant drops the four wheel proxies of the visual LOD unless you copy them. The wheels then simulate, because the Fire Geometry proxies are intact, but draw nothing, and a structural check that looks only at View and Fire Geometry passes. A smoke test with no wheels attached cannot show it either. After any rebuild of the visual LOD only (texturing, decimation, transplant), check that it still holds four wheel proxies.

## Making wheels draw

Restoring the visual wheel proxies is necessary but not enough. They also need:

1. The vanilla frame per side. `add_proxy(rotation=None)` writes py3d's identity frame, which the engine draws turned about 90 degrees, hidden in the arch. The sedan's visual LODs use, for anchor x below 0, `((-1,0,0),(0,0,1),(0,1,0))` and for x above 0 `((1,0,0),(0,0,-1),(0,1,0))`. Reframe in place by the sign of the anchor's x, overwriting the three triangle points (`canonical_proxy_triangle(anchor=current_anchor, rotation=frame_by_side, scale=0.1)`), or copy the View Geometry triangle onto the visual proxy, which keeps every selection membership.
2. The `wheel_X_Y` bone selections in the visual LOD as well as View and Fire Geometry, mapped to proxies by the same position rule, so the attached wheel has a bone and `model.cfg` has a spin target (`vehicle-proxies.md`).
3. A proxy in every visual LOD. The sedan has its wheel proxies in all visual LODs (1, 2, 3, 4 and 6) plus View and Fire Geometry; one test car had none in its second visual LOD.

With these the wheels draw on their hubs, confirmed in game. A missing visual LOD 0.0 on the wheel item was not the cause. Diagnose invisible wheels in game end to end (attached but not drawn, against not attached) and compare the proxy index and anchor with a car that draws.

A frame literal belongs to its wheel model. A working off-road test car (not vanilla) measured the opposite pair for its own wheel: for x above 0 `((-1,0,0),(0,0,1),(0,1,0))`, and its mirror for x below 0. Derive both sides with `py3d.derive_proxy_frame` from a working car that uses the same wheel item, require the new car to match, and keep a test where swapped sides must fail. The sedan's four door proxies share one frame, `((-1,0,0),(0,0,1),(0,1,0))`; the door models are mirrored per side instead.

## The original rim

The rip ships the real rim. To use it, build a custom wheel `.p3d` and point the wheel proxies at it, keeping the vanilla wheel slots and items:

- Delete the motion blur discs first (`blur*` meshes, smooth discs that hide spokes when spinning); they make the rim look solid or hollow. Remove the drive shaft too (vertices beyond about 0.10 m inboard).
- Build the tyre as a revolved flat band (walls, rounded shoulders, grooves around the tread, about 0.30 m wide); a torus reads as a balloon.
- Scale the wheel to the vanilla mesh radius of 0.359 and transplant it onto the sedan wheel model as LOD 0, keeping that model's Geometry, Memory, View and Fire LODs. The sedan wheel's config `radius` is 0.34 (`P:\DZ\vehicles\wheeled\config.cpp:4762` onward); 0.3587 to 0.359 is the radius of its mesh, a different quantity (**model knowledge**). Keep the five Memory collider points (`vehicle-geometry-and-mass.md`), or the collider shrinks to a cube and loses contact; otherwise point View and Fire Geometry at the vanilla `\dz\vehicles\wheeled\civiliansedan\proxy\sedanwheel.NNN`.
- Point the proxies by renaming the `proxy:...sedanwheel.NNN` selections to `\MyMod\<wheel>.NNN`, without `.p3d` (`vehicle-proxies.md`), keeping the vanilla per-side frame and the bone selections. Edit in place; never `add_proxy`.
- The rip ships the front left rim only; mirror it for the other corners and negate the normal X on the right side.
- Every transplanted mesh needs real UVs (`rip-structural-lods.md`, "What crashes the render").

Assemble the rim in interactive Blender: eyes catch the blur discs and the balloon tyre that scripts miss.

Wheel items are local, body chunks are in car space. A glTF or FBX export usually holds wheel vertices in car space. Before writing a separate wheel `.p3d`, find its hub, subtract it, and require every axis of the bounding box centre within 1e-4 m of 0; the host proxy then supplies the hub position once. Without this the position is applied twice. Doors, hoods and trunks are hinge-local and are not centred.

Name each wheel's damaged model to match its class: a class `Proxy...Wheel_destroyed` over a file ending `_ruined` crashed the client on the damage swap at speed (`attachment-proxies.md`).

## Changing the track width

Read the four wheel proxy frames first; it is one call. On a test car all four wheel proxies shared one frame instead of the vanilla mirrored pair, so moving the wheel mesh inside the wheel `.p3d` moved the left wheels in and the right ones out. To change the track, move each side as a whole corner:

- the proxy triangle in every LOD that has it;
- the `wheel_<side>_<axle>_*` memory points (axis, damper, damper axis, damper land, steering, steering axis);
- the `damper_land` Geometry box;
- the brake and hub chunk and its merged copies in the far LODs.

Widening that car by 10 cm (5 cm a side) moved 748 shell points and 1,570 chunk points. The limit is the brake and hub reaching the rim's inner face, not the wheel arch; compare the rim's inner profile with the brake points before testing.

## Doors from the rip

The source game ships every movable part as its own model, because it animates them. Read the `Manifest.xml` for `doors` and other movable parts before planning any cut of the body. On one car: the door sheet `scene\exterior\doors\doorlf_a`, `doorhandlelf_a`, `doorjamblf_a` and the inner card `scene\interior\doors\doorcardlf_a`, left side only (mirror the right). The hinge axes are in `Locators.xml`: `carLocator_doorLF` and `RF` (x ±0.884088, y 0.495741, z 0.006927 in source space), `carLocator_doorHandleLF` and `RF`, and `carLocator_entryDoorLF`. That is exactly the axis `model.cfg` animation sources need, under the same transform as the geometry.

When doors were fused into the body chunks, finding their faces is a matching job against the pre-cut rip pieces under the known transform (`dp = (x, z + Y0, y)`), by face signature or centroid, not a manual marking job. Build the door from its authored LODs (nine LODs, collision kept); when the inner card's authored LODs offer no lighter version, accept the higher LOD 0 count. Record each built file and where it sits in the project notes on the day it is built, or later work budgets for something already done.

What the rips ship for doors, side by side, is in `ripped-car-proxy-split.md`; why a ripped door shows an open rim is in `rip-panel-open-rim.md`.

## First person: the car's own interior

First person draws the View Pilot LOD (resolution 1100) from the seated player's head; the first-person vehicle camera `DayZPlayerCamera1stPersonVehicle` extends `DayZPlayerCamera1stPerson` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`). A free admin camera draws LOD 0 instead, so the interior can look right from outside and wrong from the seat.

- The View Pilot must carry the car's own interior. Falling back to vanilla `civiliansedan_int1` gives a mismatched, overlapping cabin.
- Facing the interior faces toward the head does not fix a one-sided rip interior: one car had 71 to 90% of faces toward the head against the sedan's 57 to 60%, and still drew only scattered pieces with the world showing through. The sedan's View Pilot holds 13 proxies, `prox_int` among them, where the test car had none.
- What worked in game: the raw glTF winding, one sided, with the interior as a dedicated proxy in the style of `prox_int` (`visual-gates-and-winding.md`). Doubling the View Pilot faces also made the interior draw, at about twice the resolved vertices, so keep it as a fallback; it fits only while the View Pilot stays under about 32k resolved vertices (one car went from 24k to 43k).
- A converted vanilla model's per-face flags are all 0 only because the converter writes 0; binarized models have no per-face flags. That number proves nothing (`rip-textures-and-materials.md`).
- A grey band over the windshield in first person was the sun visor's edge, real geometry seen because the seated camera rides high. The fix was lowering the crew proxy 5 mm, not trimming; check with a fan of rays from the eye before cutting.
