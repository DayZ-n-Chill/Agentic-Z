# Proxy frames

How a proxy triangle becomes a position and a facing, why an attached model comes out rotated or on the floor, and what changes for clothing on a static host, crew seats, body-part proxies and weapon attachments.

The names, paths and config classes below are checked on `P:\`. The frame rules are not: vanilla models on `P:\` are binarized and no text file there states how a triangle is read. Those rules are MLOD format knowledge, the behaviour of the py3d in `scripts/tools/py3d`, and in-game measurements on third-party mods. Each such paragraph starts with **Not checked on `P:\`** and says what was measured; treat it as a strong lead and confirm in game.

To fix a proxy, use `/dayz-proxy-align`. Proxy names, indexes and config classes are in `proxies.md`.

## The triangle is read by its angles

**Not checked on `P:\`** (MLOD format knowledge). The attachment frame comes from the shape of the triangle, not from the order of its vertices:

1. Sort the three corners by interior angle, largest first.
2. The largest-angle corner is the anchor: the position of the attached model.
3. The direction from the anchor to the middle-angle corner is local +Y. The direction to the smallest-angle corner is local +Z.
4. +X is Y cross Z, and Z is then made square to X and Y again.

Arma 3 tools read an MLOD proxy this way. That DayZ reads an MLOD proxy the same way is an assumption, held with high confidence because the MLOD format is the same; the in-game measurements below are what back it for DayZ.

Coordinates are raw MLOD, Y up, as py3d reads them. Because the rule is pure geometry, a frame can be worked out offline: `derive_frame` in `skills/dayz-proxy-align/scripts/proxy_frame.py` computes it, and the py3d in `scripts/tools/py3d` has the same code as `derive_proxy_frame`.

## Ambiguous triangles

A triangle whose two edges from the anchor have the same length, the 90/45/45 right triangle that hand-written proxy builders tend to emit, has no single answer: the middle and smallest angles tie, so +Y and +Z fall to raw vertex order and the frame comes out rotated. This is the usual cause of "the item is worn, but turned".

The fix is a canonical triangle with three different angles: a right angle at the anchor, a short leg along +Y and a leg twice as long along +Z (90, 63.4 and 26.6 degrees). Rotating a canonical triangle keeps its angles, so any orientation survives a write-back. `proxy_extract.py` in `/dayz-proxy-align` flags a tie as `ambiguous`, `proxy_canon.py` rewrites every proxy as a canonical triangle, and the skill's tests check the three cases offline (canonical gives identity, 90/45/45 is flagged, a rotation round-trips).

## Raw frame and engine frame

**Not checked on `P:\`** (measured in game on a third-party weapon mod and a third-party vehicle mod). The engine does not use the raw frame from the angle sort as it stands. It renders the triangle as `engine_frame = P' x raw_frame`, with

```
P' = ((-1, 0, 0),
      ( 0, 0, 1),
      ( 0, 1, 0))
```

`P'` is its own inverse, so the same matrix converts back. A rail baked with the raw identity frame rendered lying 90 degrees on its side; a raw frame of `P'` rendered upright. So a canonical triangle built from `P'` is what makes the engine draw the proxy model exactly as it was authored.

The py3d in `scripts/tools/py3d` carries both spaces. `LOD.add_proxy`, `LOD.align_proxy` and `canonical_proxy_triangle` take `space="raw"` (the default, the frame the angle sort gives) or `space="engine"` (the pose expected in DayZ), and `LOD.get_proxies` returns `raw_frame` and `engine_frame` for each proxy. Checked with py3d 1.10.1 from `scripts/tools/py3d`: `add_proxy(..., rotation=identity, space="engine")` gives a `raw_frame` equal to `P'` and an `engine_frame` equal to identity.

One point is open. `proxy_canon.py` writes the raw identity frame by default and describes it as "worn upright", because vanilla worn clothing is authored in character space. That default was written before the `P'` result above, and the two have not been compared in game on the same model. When a proxy rewritten by `proxy_canon.py` renders rotated by 90 degrees, rewrite it with `space="engine"` in py3d, or pass `--rot` for that slot.

**Not checked on `P:\`** (same tests). An offline frame or an offline render is not proof for a proxy: the vehicle body rendered rotated in game after passing the offline check twice. The check that counts is the model spawned and rendered in game, or the binarized file compared with a model that works (see Crew proxies).

## Clothing proxies on a static host

A vanilla character model carries one proxy per equipment slot: `P:\DZ\characters\bodies\bodyparts_above0.p3d` stores `proxy:\dz\characters\proxies\vest_dz.001`, `headgear_dz.001`, `legs_dz.001`, `backpack_dz.001` and the rest (byte scan), and the proxy models sit in `P:\DZ\characters\proxies\`. Each has a config class, for example `ProxyVest_DZ` at `P:\DZ\characters\data\config.cpp:10715`.

A dressable static object, such as a mannequin or an armor rack, copies that pattern: an `Inventory_Base` or `Container_Base` item whose model embeds the vanilla `\dz\characters\proxies\*_dz` proxies and whose config lists clothing slots in `attachments[]`. When its proxies are ambiguous or misplaced, equipped clothing shows at the floor, floats, clips or is turned.

- Preview against the worn model, not the ground model. Vanilla ships each item as `_m` (worn, male), `_f` (worn, female) and `_g` or `_ground` (lying on the ground); the config side is in `_shared/wearables/references/models-and-proxies.md`. Picking the ground model is the classic cause of "it shows the floor model". When a slot has several candidates, such as `plate_carrier_m` and `plate_carrier_holster_g` in `P:\DZ\characters\vests\`, choose one on purpose and tell the user which.
- Aligning the anchor does not make the engine swap the slot's default `*_dz` proxy for the equipped item's worn model. **Not checked on `P:\`** (seen on a mannequin mod): on a static `Inventory_Base` that swap is config and skeleton behaviour, a separate problem from where the anchor sits.

## Crew proxies

A seat is a proxy too. Vanilla has two crew proxy models, `ProxyCrew_Driver` at `P:\DZ\vehicles\wheeled\config.cpp:23890` and `ProxyCrew_Cargo` at `P:\DZ\vehicles\wheeled\config.cpp:23895`. `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` stores `proxy:\dz\vehicles\wheeled\proxies\crew_driver.001` once and `crew_cargo.001` to `.003` for its other three seats (byte scan); `P:\DZ\vehicles\singletrack\motorbike_02\motorbike_02.p3d` stores `crew_driver.001` and `.002`. The config names the seat's proxy with `proxyPos`, for example `proxyPos="crewDriver"` at `P:\DZ\vehicles\wheeled\config.cpp:270`, and script reads the seat transform with `CrewTransform` (`P:\scripts\3_game\vehicles\transport.c:200`). The config and script side of seats is in `_shared/vehicles/attachments-and-crew.md`.

**Not checked on `P:\`** (measured in game on a quad mod). Crew proxies are read by the same angle sort, and the 90/45/45 tie breaks them the same way. Driver and co-driver proxies made as 1 mm 90/45/45 triangles left both riders sitting sideways and turned the player on get-in. The tie resolved differently on each seat (on one, +Y ended up as "up"; on the other, as "forward"), so one bug looked like two. The fix was canonical triangles with +Y along the vehicle's forward direction and +Z up.

**Not checked on `P:\`** (same quad mod). The anchor of the crew proxy sets where the seated player is, height included. The seat comes from the proxy, not from a memory point or a bone. Anchors at Y 1.46 and 1.70 left the riders in the air until they were lowered to the real seat height.

**Not checked on `P:\`** (measured in game on a motorbike mod, DayZ 1.30.164014 experimental). `CrewTransform` returned the binarized proxy's rows conjugated by `R = diag(-1, 1, -1)`, with origins through the same `R`: the engine's crew model space is the binarized file's space turned 180 degrees about Y. A crew proxy positions and yaws the rider and nothing more. A proxy pitched 20 degrees forward still seated the player upright, with a fixed yaw of about 17 degrees and the hips 35 cm back; a 20 degree roll left the player standing about 30 cm beside the bike. Leaning or crouching needs animation. Measure what the engine did from the player's frame and bones in vehicle space, not by eye.

**Not checked on `P:\`** (same motorbike mod, same build). A crew proxy authored as the raw identity frame came out of Binarize with rows aside -X, up +Z, dir +Y, while the vanilla `Motorbike_02` proxies read identity in the same reader; in game the driver stood sideways and spun on get-in. Write crew proxies with `space="engine"` and the frame the vanilla model has after Binarize, which is identity for crew and wheels.

**Not checked on `P:\`** (same motorbike mod), on how to check a crew proxy:

- Check the file the engine reads. Compare every proxy of the binarized export with the vanilla equivalents, using the same ODOL reader for both.
- Prove the check both ways: it fails on the build known to be broken and passes on vanilla compared with itself.
- A checker that derives the frame again with the exporter's own convention agrees with its own mistake. A check that compares the binarized file with what was requested only proves the file holds what was written, not what the engine does with it.
- Before building rotated variants, pin the convention on a working reference: how a vanilla binarized model stores a known rotation, or a small rotation per axis checked in game.
- Do not copy a frame raw from another model's proxy. The `bus_*` proxies of a third-party bus mod are not vanilla `crew_*` proxies, and the right frame depends on the proxy model. For vanilla crew proxies, +Y points forward.

## Body-part proxies

A proxy can hold plain geometry: a part of the body split off into its own model, with no config class. Vanilla does this on the sedan, whose model stores `proxy:\dz\vehicles\wheeled\civiliansedan\proxy\prox_int.002` and `sedan_engine.001` (byte scan of `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`; the models are `P:\DZ\vehicles\wheeled\civiliansedan\proxy\prox_int.p3d` and `sedan_engine.p3d`), and no vanilla `config.cpp` under `P:\DZ\` has a `Proxyprox_int` or `Proxysedan_engine` class.

**Not checked on `P:\`** (measured in game on a third-party vehicle mod; geometry ranges measured on vanilla proxies converted back to MLOD and on two other vehicle mods). A mod uses this to keep one model under the Binarize vertex limit: the part becomes a model with one visual LOD and no config class, referenced as for example `proxy:\<mod>\proxy\chassis.001`. Two things must both be right:

1. The geometry is authored in model space, at its real place on the vehicle, not centered on its own origin. The vanilla cabin proxy `prox_int` spans Y 0.36 to 1.56 and `sedan_engine` spans Z -2.30 to -1.12, at the front. Centering each part on its own origin piles them all up at the host's origin.
2. The triangle's raw frame is `P'` (see Raw frame and engine frame), so the engine draws the part as authored. With the raw identity frame the body rendered lying about 90 degrees on its side. An origin anchor with the raw identity frame passes an offline check and is still wrong in game.

Other points from the same tests:

- The proxy path has no `.p3d` extension. The engine adds it, and a path that ends in `.p3d` asks for `.p3d.p3d`: the proxy is silently absent in game.
- Attachment proxies such as wheels, crew and doors are not a guide for placing a body part. Physics and config place those (`proxyPos`, the axles), and their own positions mislead.
- The vertex limit is not the 65535 the format suggests. One model loaded with 46,133 resolved vertices and failed with 46,134 (`dayz-p3d-audit/references/winding-diagnostics.md`), so run Binarize to find the limit for the model in hand.

## Weapon attachment proxies

A weapon's proxies place its attachments the same way. `P:\DZ\weapons\pistols\fnx45\fnp45.p3d` stores `proxy:\dz\weapons\attachments\magazine\magazine_fnp45.001`, `proxy:\dz\weapons\attachments\optics\optic_fnp45_mrds.001` and `proxy:dz\weapons\attachments\muzzle\suppressor_45acp.001` (byte scan; the last one is stored without the leading backslash). Each attachment model has its config class: `ProxySuppressor_45ACP` at `P:\DZ\weapons\attachments\muzzle\config.cpp:1750`, `ProxyOptic_Reflex` at `P:\DZ\weapons\attachments\optics\config.cpp:3182`, `ProxyMagazine_FNP45` at `P:\DZ\weapons\attachments\magazine\config.cpp:9383`. Slots and config are in `_shared/weapons/attachments.md`.

**Not checked on `P:\`** (measured in game on a third-party weapon mod: a compensator, a rail mount and an optic):

- The `P'` rule above was found here. A rail baked with the raw identity frame rendered lying 90 degrees on its side; a raw frame of `P'` rendered upright.
- Copying a vanilla item's frame works only when the model is authored like the vanilla one. The vanilla `optic_reflex` and the magazine worked with the vanilla frame copied value for value. A custom muzzle device authored on other local axes rendered rotated at the same frame.
- Find the bore by the hole, not by the bounding box. A custom compensator had a round bore hole, an oval vent hole, and a tab at right angles that was longer than the bore. The longest bounding box axis and a search for the central hollow both picked the wrong axis. What worked: render the muzzle view, an orthographic view straight down the barrel at the current proxy frame, and find the round hole. The barrel passes through the round one.
- The fix is a shift and a roll. Find the center of the round hole in the plane across the barrel, move the proxy triangle so that center lands on the barrel line, and apply the roll about the barrel axis that is needed (for 180 degrees with the barrel along X: `p -> (p.x, 2*Yb - p.y, -p.z)`, where `Yb` is the barrel's height). Render the muzzle view again and compare with the user's in-game screenshot before building.
- The inventory preview does not use the proxy. It draws the attachment's own model, so fixing the proxy fixes the gun in game while the icon still shows the model's authored facing. To make them match, bake the proxy's engine orientation `M` into the attachment model (rotate every LOD's points, the normal pool and the memory points by `M`) and reset the proxy to the canonical triangle for `P'`. In game nothing changes, since `anchor + I(Mv)` equals `anchor + Mv`, and the preview now shows the in-game facing.

This repo has no script for the muzzle view, the hole search or the bake; the method above is enough to write them.
