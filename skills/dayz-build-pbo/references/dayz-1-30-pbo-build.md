# DayZ 1.30 and packing

What DayZ 1.30 changes for packing a mod: a member defined twice now stops binarize, an unpacked mod folder can be loaded, and the PBO header property `fsShadowing` lets a PBO shadow vanilla files. The rest of the pre-build contract (folder structure, `stringtable.csv`, the include list, ODOL non-determinism) holds as before; `pre-build-checks.md` starts from it.

All of this is game and tool behaviour on DayZ 1.30, which vanilla files on `P:\` cannot confirm. The version that matters is named where a fact needs it.

## A member defined twice stops binarize

Up to 1.29 the pre-build check was "the same class cannot be defined twice", and a property written twice in one class was silent, with the last one winning. Since 1.30 the binarizer stops when a member is defined more than once in one class. AddonBuilder and CfgConvert, which used to pass a repeated `scope`, `displayName`, `weight`, `hiddenSelections[]` or inner class name, now fail, and `build.py` prints binarize's `Member already defined` line from AddonBuilder's log.

The check is in the engine; the vanilla scripts hold no example of it. Audit every `config.cpp`, and every fragment it includes, for a member written twice in the same class body. A forward declaration followed by the definition (`class Foo;` then `class Foo: Bar {}`) is not this fault. The check in `pre-build-checks.md` covers both duplicate class names and duplicate members.

## Unpacked mods do not replace the PBO

Since 1.30, `-mod` can name a folder and RV configs load unpacked. That is a way to iterate in diag (`/dayz-launch-test`). Workshop and dedicated server releases still need a PBO, so never skip AddonBuilder for a release because unpacked loading exists.

Regenerating a 1.30 navmesh `.nm` file is a terrain and Workbench task, not a packing check. Mention it in the release notes of a custom map; this skill does not check `.nm` files.

## `fsShadowing`: a second PBO with a vanilla prefix

Since DayZ 1.30 Update 2 the PBO header property `fsShadowing=1` lets a PBO load even when its prefix matches one already loaded, so its files shadow the vanilla files at the same paths. Vanilla PBO headers do not carry it. A shadow PBO hides only the files it holds: with two shadow PBOs that held only layouts, the rest of vanilla `gui` still loaded. What a layout variant does and how to write one is in `skills/_shared/ui/layout-variants.md`.

Measured in diag on 1.30 with a Workbench-generated layout variant: a PBO whose prefix file was the bare line `gui`, packed by a third-party packer with an option for the property, held `config.bin`, the `.layout` and its `.layout.meta`. Its header read back as `prefix=gui` and `fsShadowing=1`, it loaded unsigned and the variant applied in game.

Check such a PBO two ways: its header shows both properties, and it holds only the files it means to shadow. A `.meta` beside each variant `.layout` is optional, and so is `config.cpp`: variants packed without them applied too.

## Which packer can write the property

| Packer | What it writes | Notes |
|---|---|---|
| MakePbo | A prefix file with the two lines `prefix=gui` and `fsShadowing=1` gives the header `prefix=gui`, `fsShadowing=1`, plus a stamp of MakePbo's own library and a `version=` stamp. | Compiles `config.cpp` to `config.bin` and leaves the prefix file out. Without a `config.cpp` it writes no prefix. PBOs built this way loaded unsigned in diag and their variants applied. |
| AddonBuilder | `product=dayz ugc` and `prefix` only. | Has no option for the property. A folder without `config.cpp` gets an empty one packed, together with the prefix file. |
| FileBank (`Bin\PboUtils\FileBank.exe`, the DayZ Tools packer AddonBuilder calls) | Any property you pass, and needs no `config.cpp`. | See the command below. |

The FileBank call that gave the header `prefix=gui`, `fsShadowing=1` and nothing else:

```bat
FileBank -property prefix=gui -property fsShadowing=1 -exclude <list file> -dst <out folder> <folder>\gui
```

A list file holding the line `$PBOPREFIX$.txt` keeps the prefix file out. The PBO is named after the source folder (`gui.pbo`). One built this way, holding only a layout variant and installed under another name, loaded unsigned in diag and its variant applied.
