# Proxies

A proxy is a placeholder in one model that shows another model in its place: furniture in a house, a lock on a gate, a plank on a fence under construction.

## In the model

- In Object Builder a proxy is a single triangle with a named selection `proxy:<path>.<index>`. The triangle sets where the other model sits and which way it faces. That part is Object Builder format knowledge; the names below are what vanilla stores.
- The facing comes from the triangle's shape, not from the order of its vertices: the corner with the widest angle is the position, and the other two corners give the axes. A triangle with two equal angles, such as 90/45/45, has no single answer and the other model comes out turned. The rule, the unambiguous triangle to use instead, and the difference between the raw frame and the frame the engine draws are in `proxy-frames.md`.
- `<path>` is the other model's path from the root of `P:\`, starting with a backslash, without `.p3d`. `<index>` is a three digit number that tells copies of the same model apart. Measured in game on a third-party vehicle mod, not checked on `P:\`: a path written with `.p3d` asks the engine for `.p3d.p3d`, and the proxy is silently absent in game.
- Vanilla examples, stored in `P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d`: `proxy:\dz\structures\furniture\lighting\fluor_lamp\fluor_lamp.001` up to `fluor_lamp.006`, one per lamp. `P:\DZ\gear\camping\fence.p3d` uses both `.000` and `.001`, for example `proxy:\dz\gear\consumables\single_plank.000` and `proxy:\dz\gear\camping\combination_lock3.001`.
- Across the game: the models under `P:\DZ\` store 17,891 proxy selections, counting each name once per model. Index `001` is the most common (5,104) and `000` appears 529 times. 147 of the names keep `.p3d` before the index, for example `proxy:dz\structures\furniture\various\debris_small_house.p3d.003` in `P:\DZ\structures\military\airfield\mil_aircraftshelter.p3d`; the other 17,744 do not. So binarized vanilla files hold both spellings, and the form without `.p3d` is the one to write.
- Put the proxy in every visual LOD where the other model should show. A proxy left out of a lower LOD makes that part vanish at a distance.
- Since 1.30, a proxy that shows an inventory attachment also goes in the View Geometry LOD: a dedicated server reads the attachment's position from there when the proxy is not in the last visual LOD, instead of returning the parent's center (`lods.md`, View Geometry).
- Vehicle slot proxies sit in non visual LODs as well. `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` has five visual LODs and one LOD at resolution `1100` and stores each wheel proxy (`sedanwheel.001` to `.005`) 7 times and `battery_car.001` 8 times; the wheel slot case is in `selections.md`.
- The index does not choose a slot. `P:\DZ\gear\camping\territory_flag.p3d` stores `proxy:\dz\gear\consumables\stone.001` for the stones of the flag pole, although `Material_FPole_Stones` is the second entry of `inventorySlot[]` in `ProxyStone` (`P:\DZ\gear\consumables\config.cpp:4573`). A proxy is tied to its slot through the selection that the slot's `CfgSlots` class names (`selection="Material_FPole_Stones"`, `P:\scripts\config.cpp:2496`).
- Point at a model inside the mod's own `$PBOPREFIX$` or at a vanilla model. Never point at a `P:\` drive letter path.
- Tool knowledge: the py3d in `scripts/tools/py3d` writes a proxy with `LOD.add_proxy(path, index)`. It refuses a path that ends in `.p3d` and an index below 1, and it writes a triangle whose facing is unambiguous.

## In config

A proxy that shows an attachment needs a `CfgNonAIVehicles` class named `Proxy` plus the proxy model's file name, with that model and the slots it serves. Vanilla: `Proxysingle_plank: ProxyBaseBuilding` with `model="\DZ\gear\consumables\single_plank.p3d"` and the plank slots (`P:\DZ\gear\camping\config.cpp:13405`), under `ProxyBaseBuilding: ProxyAttachment` (`:13401`). The class is written by `dayz-config-specialist`; send it the proxy path, the class name and the slot names.

A proxy that is only decoration needs no config of its own: no vanilla `config.cpp` under `P:\DZ\` has a `Proxyfluor_lamp` class for the house lamps above.

For an item, write a `ProxyAttachment` class of the mod's own rather than adding the slot to a vanilla vehicle part class. Measured in one in-game test on a third-party item, not checked on `P:\`: a slot added with `inventorySlot[] +=` to the vanilla `ProxyBattery_Car` (`P:\DZ\vehicles\parts\config.cpp:1145`) never drew the battery on an `ItemBase` flag, in three proxy layouts, while a class of the item's own deriving from `ProxyAttachment`, with its own small proxy model, drew it. `ProxyBattery_Car` derives from `ProxyPart`, a vehicle part class with `reversed=1` (`P:\DZ\vehicles\parts\config.cpp:1125`); the vanilla flag's own proxy class is `ProxyDZ_Flag: ProxyAttachment` (`P:\DZ\gear\camping\config.cpp:13595`). The full account is in `dayz-model-pipeline/references/config-and-packing.md`.

A proxy that points at a binarized vanilla model can disappear in game. That is not checked on `P:\`; the cases are in `dayz-model-pipeline/references/community-findings.md`.

Two more findings measured on third-party mods, not checked on `P:\` (`dayz-model-pipeline/references/memory-and-selections.md`):

- Binarize does not merge the proxied model into the parent. Converting the binarized parent back and finding the proxy there shows only that the proxy survived; whether the other model sits right can be seen only in game.
- An entity can be nothing but proxies: a visual LOD holding only proxy triangles, plus Memory, View Geometry and Fire Geometry boxes and no Geometry LOD, drew its attachments, appeared in the vicinity panel and kept its attachments across restarts. It still blocked the player through its bounding volume.

Clothing and gear proxies, including the body proxies on the survivor, are in `_shared/wearables/references/models-and-proxies.md`.

## When the other model shows in the wrong place

An attached item that sits on the floor, floats, clips or is turned has a proxy triangle that is misplaced or ambiguous. `/dayz-proxy-align` reads every proxy of an MLOD host, shows them in a browser editor against the worn clothing, rewrites them as unambiguous triangles and writes them back with py3d, leaving the rest of the model as it was.

`proxy-frames.md` has the rules that skill applies, and the cases that behave differently:

| Proxy | What is different |
|---|---|
| Clothing slots on a static host (a mannequin or an armor rack) | The item to preview against is the worn model, not the ground model. |
| Crew seats (`ProxyCrew_Driver`, `P:\DZ\vehicles\wheeled\config.cpp:23890`) | The anchor sets where the player sits; only position and yaw reach the rider. |
| Body parts with no config class (`P:\DZ\vehicles\wheeled\civiliansedan\proxy\prox_int.p3d`) | The part's geometry is authored at its real place on the host. |
| Weapon attachments (`ProxySuppressor_45ACP`, `P:\DZ\weapons\attachments\muzzle\config.cpp:1750`) | The inventory preview draws the attachment's own model and ignores the proxy. |
