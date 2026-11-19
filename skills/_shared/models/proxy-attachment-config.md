# Proxy attachment classes

How the `CfgNonAIVehicles` class that makes an attached item visible is named and written, and why an item needs a proxy class of its own rather than a slot added to a vanilla vehicle part. It is the config third of the proxy system; the model side is in `proxies.md` and `memory-and-selections-authoring.md`, and the py3d code for the triangle and the proxy model is in `py3d-proxies.md`.

Without this class the attachment is in the inventory but invisible on the model.

## The class

Vanilla declares `class ProxyAttachment;` (`P:\DZ\gear\camping\config.cpp:13396`) and maps the plank slots to their model in `Proxysingle_plank` (`:13415`). A mod writes the same shape:

```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;                                 // declare it, or the build fails

    class ProxyMySlot: ProxyAttachment
    {
        scope = 2;
        inventorySlot[] = {"CarBattery", "TruckBattery"};  // vanilla slot names
        model = "\MyAddon\data\MySlot.p3d";                // "Proxy" + this base name = the class name
    };
};
```

Rules:

- Declare `class ProxyAttachment;` first; without it Addon Builder fails with an undefined base class. The base itself is in the engine config, `CfgNonAIVehicles` at `P:\bin\config.cpp:2276` to `:2285`: `scope=0`, `simulation="ProxyInventory"`, `autocenter=0`, `animated=0`, `shadow=1` and `reversed=1`. Your class inherits all of them, so it only has to set `scope = 2`, the slots and the model.
- `inventorySlot[]` matches the slot names in `attachments[]` of the parent `CfgVehicles` class.
- `model` points at the proxy `.p3d`, which must exist in the addon.
- The class name is `Proxy` plus the base name of `model`, compared without case (`MySlot.p3d` gives `ProxyMySlot`). A class named any other way draws nothing and logs nothing, inventory slots included. Measured in game on a mod quad, not checked on `P:\`: its three inventory slots drew nothing until their proxy classes were renamed (`_shared/vehicles/attachment-proxies.md`, "Check the proxy class name first"). Check the name in `config.cpp` before measuring any proxy frame.
- The class name must be unique across every loaded addon, so the proxy model's base name must be too.
- Several slots can share one proxy model.
- Vanilla slots (`CarBattery`, `TruckBattery`, `SparkPlug` and the rest) need no `CfgSlots` entry of their own.

The battery adapter of a power grid mod:

```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;
    class ProxyPM_BatterySlot: ProxyAttachment
    {
        scope = 2;
        inventorySlot[] = {"CarBattery", "TruckBattery"};
        model = "\PowerMod\data\battery_adapter\PM_BatterySlot.p3d";
    };
};
```

## Give an item its own class, not a vanilla vehicle part's

On an item, a slot added to the vanilla `ProxyBattery_Car` drew nothing. Measured in game on one power grid mod item, not checked on `P:\`:

- The item was an `ItemBase` flag whose slot `PM_FlagBattery` held a `CarBattery`. The slot was added with `inventorySlot[] +=` to `ProxyBattery_Car`, the class of the vanilla proxy `\dz\vehicles\parts\battery_car.001`.
- That class derives from `ProxyPart`, a vehicle part class (`ProxyBattery_Car` at `P:\DZ\vehicles\parts\config.cpp:1145`; `ProxyPart`, with `simulation="ProxyInventory"` and `reversed=1`, at `:1125` to `:1135`).
- It never drew the battery in three layouts, each adding to the one before: the proxy in LOD 0; the proxy inside a named selection called like the slot, which the slot's `CfgSlots` `selection` names, as `civiliansedan` holds `battery_car.001` inside its `battery` selection; and copies of the proxy in the Geometry, View and Fire Geometry LODs, the only LODs where `battery_charger.p3d` carries it.
- A class of the item's own drew it: `class ProxyPM_FlagBattery: ProxyAttachment` with `inventorySlot[] = {"PM_FlagBattery"}`, its own minimal proxy model `PM_FlagBattery.p3d` at `model`, and the proxy triangle in LOD 0. That is how the vanilla flag does it, with `ProxyDZ_Flag: ProxyAttachment` (`P:\DZ\gear\camping\config.cpp:13605`). In a build with both proxies 0.35 m apart, the battery appeared at the item's own.

So for an item, write a `ProxyAttachment` class of your own as above. The two bases do not differ in facing: `ProxyAttachment` carries the same `simulation`, `autocenter`, `shadow` and `reversed=1` as `ProxyPart` (`P:\bin\config.cpp:2276` to `:2285`). Why the vehicle part class still drew nothing on an item is not visible in config.

A proxy that only decorates needs no class: no vanilla `config.cpp` under `P:\DZ\` has a class for the house lamps of `proxies.md`.
