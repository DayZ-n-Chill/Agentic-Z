# Common validation failures

Which failures the pre-build checks report most often, what causes each one and how to fix it. The checks themselves are in `pre-build-checks.md`.

## Quick table

| Report | Cause | Fix |
|---|---|---|
| Unclosed brace in `config.cpp` | A class is missing its closing `}`. | Count the `{` and `}` pairs, most often in a long class. An editor with brace matching finds it fast. |
| Missing semicolon after a property | A property or array has no `;` at its end. | End every property and array with `;`, and close every class with `};`. |
| Texture not found | The path is wrong or the file is missing. | Check the capitalisation, since paths are case sensitive on a Linux server, and put the `.paa` at exactly that path. |
| `hiddenSelections` count mismatch | `hiddenSelectionsTextures[]` or `hiddenSelectionsMaterials[]` has a different length from `hiddenSelections[]`. | Give each array one entry per selection, in the same order (example below). |
| Missing `ce_center` in the Memory LOD (a warning) | The `.p3d` has no `ce_center` memory point, so script falls back to the object's position raised by 0.2 m. | Add it as a memory point in the Memory LOD with Object Builder or py3d when the item's middle is far from its origin. |

`ce_center` is the object's centre for actions and the vicinity list, not its centre of mass: `GetCenter` (`P:\scripts\3_game\entities\object.c:1361`) reads it when it exists (`:1363`) and otherwise returns the object's position raised by 0.2 m (`:1371`). Most vanilla models have none, so a missing point is not a load error.

The three arrays line up index by index:

```cpp
hiddenSelections[] = {"skin1", "skin2"};
hiddenSelectionsTextures[] = {"tex1.paa", "tex2.paa"};
hiddenSelectionsMaterials[] = {"mat1.rvmat", "mat2.rvmat"};
```

The engine accepts a shorter array (`config-and-model-checks.md` explains why this is a warning).

## A custom weapon stuck in one fire mode

The weapon fires only semi automatic, the fire mode key does nothing and the HUD shows no mode name. Binarize says nothing.

The cause is `class Mode_SemiAuto;` and `class Mode_FullAuto;` declared inside `class CfgWeapons`. That creates empty stubs at `CfgWeapons.Mode_FullAuto` that hide the real classes at the config root, where vanilla defines `class Mode_FullAuto: Mode_SemiAuto` with `autoFire=1` (`P:\bin\config.cpp:315` to `:318`). A mode that inherits the stub has no `autoFire`, so the engine drops it. A forward declaration is a valid external, so CfgConvert and binarize never warn and the decoded `config.bin` looks right.

Move `class Mode_SemiAuto;` and `class Mode_FullAuto;` to the root, above `class CfgWeapons` and beside `class OpticsInfoRifle;`, as vanilla weapon configs do (`P:\DZ\weapons\firearms\ak101\config.cpp:18` to `:24`), then check the built config by decompiling the PBO's `config.bin`. To isolate the cause, add a test clone `WeaponName_ModeTest: VanillaWeapon_Base` that only inherits and names no `Mode_*` class: if it cycles modes, the fault is your `Mode_*` reference. More in `skills/_shared/weapons/recoil-fire-modes.md`.

## A stringtable key that shows its own name

`#STR_MYKEY` is used in code, config or a `.layout` but has no row in the stringtable. The engine says nothing: the key prints its own name on screen and the client RPT holds no line about it (measured in game).

Add a row to `stringtable.csv` at the addon root. DayZ reads CSV, not the `stringtable.xml` of Arma 3. The key goes in column 1 without the leading `#`, and the header carries the seven columns `stringtable-and-script-checks.md` asks for; with a four-column header every key stays unresolved.

```csv
"Language","original","english","spanish","german","russian","chinesesimp"
"STR_MYKEY","My Item Name","My Item Name","Mi objeto","My Item Name","My Item Name","My Item Name"
```

## Binarize stops on a member defined twice

Since DayZ 1.30 the same member (`scope`, `displayName`, `weight`, `hiddenSelections[]`, an inner class) written twice in one class body stops binarize, and `build.py` prints binarize's `Member already defined` line from AddonBuilder's log. Delete or merge the extra line so each member appears once per class block, then rebuild. What changed and how to audit for it: `dayz-1-30-pbo-build.md`.
