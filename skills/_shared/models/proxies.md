# Proxies

A proxy is a placeholder in one model that shows another model in its place: furniture in a house, a lock on a gate, a plank on a fence under construction.

## In the model

- In Object Builder a proxy is a single triangle with a named selection `proxy:<path>.<index>`. The triangle sets where the other model sits and which way it faces. That part is Object Builder format knowledge; the names below are what vanilla stores.
- `<path>` is the other model's path from the root of `P:\`, starting with a backslash, without `.p3d`. `<index>` is a three digit number that tells copies of the same model apart.
- Vanilla examples, stored in `P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d`: `proxy:\dz\structures\furniture\lighting\fluor_lamp\fluor_lamp.001` up to `fluor_lamp.006`, one per lamp. `P:\DZ\gear\camping\fence.p3d` uses both `.000` and `.001`, for example `proxy:\dz\gear\consumables\single_plank.000` and `proxy:\dz\gear\camping\combination_lock3.001`.
- Put the proxy in every visual LOD where the other model should show. A proxy left out of a lower LOD makes that part vanish at a distance.
- Point at a model inside the mod's own `$PBOPREFIX$` or at a vanilla model. Never point at a `P:\` drive letter path.

## In config

A proxy that shows an attachment needs a `CfgNonAIVehicles` class named `Proxy` plus the proxy model's file name, with that model and the slots it serves. Vanilla: `Proxysingle_plank: ProxyBaseBuilding` with `model="\DZ\gear\consumables\single_plank.p3d"` and the plank slots (`P:\DZ\gear\camping\config.cpp:13405`), under `ProxyBaseBuilding: ProxyAttachment` (`:13401`). The class is written by `dayz-config-specialist`; send it the proxy path, the class name and the slot names.

A proxy that is only decoration needs no config of its own: no vanilla `config.cpp` under `P:\DZ\` has a `Proxyfluor_lamp` class for the house lamps above.

Clothing and gear proxies, including the body proxies on the survivor, are in `_shared/wearables/references/models-and-proxies.md`.
