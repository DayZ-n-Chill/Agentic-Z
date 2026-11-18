# Config and model.cfg checks

What to check in `config.cpp` and `model.cfg` before packing: syntax, `CfgPatches`, inheritance, the `hiddenSelections` arrays, duplicates, and whether `model.cfg` matches the models it describes. Most mod failures start in `config.cpp`. The other pre-build checks are indexed in `pre-build-checks.md`.

## `config.cpp`

| Check | Rule |
|---|---|
| Brace balance | Count `{` and `}` to find an unclosed class. |
| Semicolons | Every property and array ends with `;`, and every class closes with `};`. |
| `CfgPatches` | Exists, with at least one patch class. |
| Patch members | Vanilla patches carry `units[]`, `weapons[]`, `requiredVersion` and `requiredAddons[]` (`CfgPatches` at `P:\DZ\gear\tools\config.cpp:1`), but the engine accepts a patch without them: vanilla `DZ_data_aiconfigs` has an empty body (`P:\DZ\data\aiconfigs\config.cpp:3`). `/dayz-lint` warns on a missing `units[]` or `weapons[]`, fails on a missing `requiredAddons[]` (without it the load order after the vanilla classes the mod changes is not guaranteed), and does not check `requiredVersion`. |
| Inheritance | The parent class exists, such as `Inventory_Base`, `Container_Base` or `Land_Stone_*`. Warn when the parent is not a known DayZ base. |
| `AnimationSources` | Every source defined here is used in `model.cfg`, when there is one. |
| Duplicate class names | The same class is not defined twice. |
| Duplicate members | Since 1.30 a member defined twice in one class body stops the binarizer. A forward declaration followed by the definition (`class Foo;` then `class Foo: Bar {}`) is not this fault. See `common-validation-failures.md` and `dayz-1-30-pbo-build.md`. |
| Foreign syntax | Reject obvious Python or macro syntax in a `.cpp`; the compiler may not catch it. |

### `hiddenSelections` arrays: a warning, not a rule

`hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` are each read index by index against `hiddenSelections[]`, so entry N retextures selection N. Giving each array, when present, the same length as `hiddenSelections[]` is a mod-side habit that makes every selection's texture and material explicit.

The engine accepts a shorter array. Vanilla `Flashlight` has four `hiddenSelections`, four `hiddenSelectionsTextures` and one `hiddenSelectionsMaterials` entry (`P:\DZ\gear\tools\config.cpp:278` to `:295`), so a length mismatch is a warning, never a failure. The simplest vanilla shape is one selection (`:79`) with one texture (`:83`).

Sample report lines:

```text
[FAIL] config.cpp line 15: unclosed brace (1 extra {)
[FAIL] config.cpp line 42: missing semicolon after property "units[]"
[PASS] CfgPatches valid (1 patch: MyMod_Item01)
[WARN] Inheritance: parent "CustomBase_Broken" not recognised (may not exist)
[PASS] hiddenSelections arrays aligned (3 selections, 3 textures, 3 materials)
[FAIL] Duplicate class "Item_Torch" at lines 28 and 105
[FAIL] Member "scope" defined twice in class "MyItem" (stops the 1.30 binarizer)
```

## `model.cfg`

Check it only when the addon has one.

| Part | Check |
|---|---|
| `CfgSkeletons` | Every bone in `skeletonBones[]` exists and is unique, names are lower case with underscores, and no bone is its own ancestor. |
| `CfgModels` class name | Matches the `.p3d` file name, case included: class `Item_Compass` for `Item_Compass.p3d`. |
| `CfgModels` parent | Each class inherits `Default` or another class declared in the same `CfgModels`. |
| Animation `selection` | Exists as a named selection in the matching `.p3d`. |
| Animation `axis` | Exists as a memory point pair in the `.p3d`, such as `axis_lever` and `axis_lever_end`. |
| Animation `source` | Matches an `AnimationSources` name in `config.cpp`. |

A class name that does not match its `.p3d` fails without a word and does real harm. The engine falls back to `CfgModels.Default`, which has no skeleton and no sections, for that model. On a weapon the attachment proxies stop rendering: attachments still attach and show in their slots, and the loose item still renders in the world, but they are invisible on the weapon in hands, in the inventory preview and on the ground, with no RPT error. The usual trigger is renaming a model, such as `body.p3d` to `body_raised.p3d` for a grip change, without updating `CfgModels`. Fix it with `class <new>: <old> {};`, and run this check again after any model rename.

Sample report lines:

```text
[PASS] Skeleton defined (5 bones)
[FAIL] model.cfg class "Item_Watch" does not match the .p3d file name (found Item_WatchGold.p3d)
[WARN] Animation "door_open": selection "door_frame" not in the named selections
[FAIL] Animation "lever_rotate": axis end "lever_axis_end" not found in the p3d
[PASS] Animation source "click_anim" matches config.cpp AnimationSources
```
