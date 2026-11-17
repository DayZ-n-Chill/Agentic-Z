# Common validation failures and fixes

Symptom, cause and fix for the failures the pre-build checks report most often.

### FAIL: Custom weapon stuck in single-mode (only fires semi; fire-mode key does nothing; no mode name in HUD) — binarize stays silent
**Cause:** `class Mode_SemiAuto;` / `class Mode_FullAuto;` forward-declared INSIDE `class CfgWeapons` creates an empty stub at `CfgWeapons.Mode_FullAuto` that eclipses the real one (`Mode_FullAuto: Mode_SemiAuto` with `autoFire=1` at root scope, vanilla `P:\bin\config.cpp:315` to `:318`). Subclasses inherit the stub without `autoFire` → engine discards the mode. A forward-decl is a valid external, so CfgConvert/binarize never warns and the de-rapped .bin looks perfect.
**Fix:** Move `class Mode_SemiAuto;` / `class Mode_FullAuto;` to ROOT scope (above `class CfgWeapons`, alongside `class OpticsInfoRifle;`). Verify with `bin.pbo` decompilation. A diagnostic clone `WeaponName_ModeTest: VanillaWeapon_Base` (pure inherit, no `Mode_*` refs) that cycles isolates the cause to your `Mode_*` reference. See `skills/_shared/weapons/recoil-fire-modes.md` (fire mode bases at the config root).

### FAIL: "Unclosed brace in config.cpp"
**Cause:** Missing closing `}` in a class definition
**Fix:** Count all `{` and `}` pairs, especially in large classes. Use a code editor with brace matching (Sublime, VS Code).

### FAIL: "Missing semicolon after property"
**Cause:** Forgot `;` at end of property or array
**Fix:** Every line in config.cpp must end with `;` (except opening `{`)
```cpp
class MyClass {
    displayName = "My Item";  // <-- MUST have semicolon
    scope = 2;
};
```

### FAIL: "Texture not found: data\textures\..."
**Cause:** Referenced texture doesn't exist or path is wrong
**Fix:** Check capitalization (paths are case-sensitive on a Linux server). Ensure .paa file is in exact path.

### FAIL: "#STR_KEY missing from stringtable.csv"
The sample below carries the seven-column header that `pre-build-checks.md` check 6 calls for; with a
four-column header every key stays unresolved.
**Cause:** Used `#STR_MYKEY` in code, config or a `.layout` but didn't add it to the
stringtable. The engine says nothing about this: the key prints its own name on screen and
logs zero RPT lines (measured over a 49,340-byte client log).
**Fix:** Add a row to `stringtable.csv` at the addon root. DayZ uses CSV, not the
`stringtable.xml` of Arma 3. The key goes in column 1
**without** the leading `#`:
```csv
"Language","original","english","spanish","german","russian","chinesesimp"
"STR_MYKEY","My Item Name","My Item Name","Mi objeto","My Item Name","My Item Name","My Item Name"
```

### WARN: "Missing ce_center in Memory LOD"
**Cause:** the `.p3d` has no `ce_center` memory point (the object's centre for actions and the vicinity list, read by `GetCenter` at `P:\scripts\3_game\entities\object.c:1363`; it is not the centre of mass)
**Fix:** Add `ce_center` as a memory point in the Memory LOD (use Object Builder or py3d).

### FAIL: "hiddenSelections count mismatch"
**Cause:** `hiddenSelectionsTextures[]` or `hiddenSelectionsMaterials[]` length differs from `hiddenSelections[]`
**Fix:** Ensure each array aligns index-by-index with `hiddenSelections[]`:
```cpp
hiddenSelections[] = {"skin1", "skin2"};                      // 2 selections
hiddenSelectionsTextures[] = {"tex1.paa", "tex2.paa"};        // 2 textures (one per selection)
hiddenSelectionsMaterials[] = {"mat1.rvmat", "mat2.rvmat"};   // 2 materials (one per selection)
// Total items in hiddenSelections (2) must match texture count (2) AND material count (2)
```

### FAIL: Binarizer stops — member defined multiple times (DayZ 1.30)
Until 1.29, duplicate **properties** inside one class were silent and the last one won. Since 1.30 the binarizer stops when a member is defined more than once in a config file; `build.py` prints its `Member already defined` line from AddonBuilder's log.
**Cause:** The same member (`scope`, `displayName`, `weight`, `hiddenSelections[]`, an inner class, …) appears twice in one class body. Duplicate **class names** were already a FAIL (`pre-build-checks.md` check 2); duplicate **members** are now a hard binarize stop too.
**Fix:** Delete or merge the extra assignment so each member appears once per class block. Then rebuild. Detail: `dayz-1-30-pbo-build.md`.
