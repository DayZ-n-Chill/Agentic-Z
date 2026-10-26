# Models and proxies

Covers the models a wearable needs, how the character picks the worn model, how proxies place attachments, how headgear hides parts of the head, and what to tell the Object Builder specialist.

## Three models per wearable

| Config key | Model | Vanilla example |
|---|---|---|
| `model` | Ground model, used in hands, on the ground and in the inventory preview. | `plate_carrier_g.p3d` at `P:\DZ\characters\vests\config.cpp:29` |
| `ClothingTypes` `male` | Worn model for male characters. | `plate_carrier_m.p3d` at `:58` |
| `ClothingTypes` `female` | Worn model for female characters. | `plate_carrier_f.p3d` at `:59` |

The character's `clothingType` decides which worn model it uses: `SurvivorMale_Base` sets `clothingType="male"` (`P:\DZ\characters\data\config.cpp:9155`) and `SurvivorFemale_Base` sets `"female"` (`:9209`). Vanilla names the files `_g`, `_m` and `_f`, or `_ground` for the ground model (`tshirt_ground.p3d`, `P:\DZ\characters\tops\config.cpp:2248`).

**Engine:** the worn models are weighted to the character skeleton so they move with the body; the ground model is a plain static model. Start a new worn model from the closest vanilla worn model's layout rather than from scratch. This is Object Builder and Blender work, not config.

## Proxies on the character

The survivor body carries one proxy per equipment slot, defined in `CfgNonAIVehicles` at `P:\DZ\characters\data\config.cpp:10657`. Examples: `ProxyHeadgear_DZ` uses `\dz\Characters\Proxies\Headgear_DZ.p3d` (`:10685`), `ProxyVest_DZ` uses `Vest_DZ.p3d` (`:10715`). The proxy models are in `P:\DZ\characters\proxies\`. A mod wearable for an existing slot needs no change here.

## Proxies on gear

A wearable that shows its attachments (pouches, holsters, grenades on a vest) has a proxy in its models for each one, and a `CfgNonAIVehicles` class that ties the proxy to a slot.

- The vanilla plate carrier models hold the proxies `\dz\characters\vests\plate_carrier_pouches_g`, `plate_carrier_holster_g` and `\dz\characters\vests\proxy\proxy_grenade_a` to `_d` (byte scan of `P:\DZ\characters\vests\plate_carrier_g.p3d` and `plate_carrier_m.p3d`).
- Each proxy model has a class named `Proxy` plus the model file name, inheriting `ProxyAttachment`, with `inventorySlot[]` and `model`. `Proxyplate_carrier_pouches_g` maps to slot `VestPouch` and model `DZ\characters\vests\plate_carrier_pouches_g.p3d` (`P:\DZ\characters\vests\config.cpp:2780`); `Proxyproxy_grenade_a` maps to `VestGrenadeA` (`:2807`). The block starts at `:2768`.
- The slot must also be in the wearable's `attachments[]` (`P:\DZ\characters\vests\config.cpp:30`).
- An attachment's proxy can point at the attachment's own ground model, as the pouches do, or at a small placeholder model under a `proxy\` folder, as the grenade slots do (`P:\DZ\characters\vests\proxy\`).

A mod that adds a new attachment point writes its own `CfgNonAIVehicles` class named after its own proxy model, inside the mod's `$PBOPREFIX$`.

## Hiding parts of the head

`headSelectionsToHide[]` lists head model selections to hide while the item is worn. It is read at `P:\scripts\4_world\entities\itembasetype.c:105`. Examples: `Clipping_HelmetMich` on `BallisticHelmet_ColorBase` (`P:\DZ\characters\headgear\config.cpp:86`), `Clipping_Mich2001` on `Mich2001Helmet` (`:8410`), `Clipping_Gasmask` on `GasMask` (`P:\DZ\characters\masks\config.cpp:57`).

The names must exist in the vanilla head models. The vanilla head `m_adam.p3d` holds `clipping_flatcap`, `clipping_gasmask`, `clipping_headtorch`, `clipping_helmetmich`, `clipping_mich2001`, `clipping_mxhelmet`, `clipping_pilotka`, `clipping_ssh68helmet`, `clipping_baseballcap` and others (byte scan of `P:\DZ\characters\heads\m_adam.p3d`). A mod cannot add a new selection to the vanilla heads, so a new hat reuses the vanilla clipping selection whose shape is closest.

## Notes for the Object Builder specialist

Hand these over in the report, one line each:

1. The three model paths (ground, male, female) under the mod's `$PBOPREFIX$`.
2. The hidden selection each model needs: `camoGround` in the ground model, `camoMale` in the male model, `camoFemale` in the female model, plus `personality` in a worn model with bare skin (see `color-variants.md`). Each one in every visual LOD.
3. Each attachment proxy: the proxy model path, the slot it serves, and where it sits on the item (for example "front center, over the plate" for a pouch).
4. The `headSelectionsToHide[]` entry chosen for headgear or masks, so the model is shaped to match what it hides.
5. The closest vanilla model to copy layout and rig from, as a `P:\DZ\characters\...` path.
