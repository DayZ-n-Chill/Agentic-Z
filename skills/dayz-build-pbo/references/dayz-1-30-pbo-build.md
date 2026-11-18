# DayZ 1.30 — PBO / binarizer deltas

What DayZ 1.30 changes for packing: duplicate members stop binarize, unpacked mods, and the `fsShadowing` header property.

Not checkable on `P:\`: this is game and tool behaviour on the DayZ 1.30 builds named in the text, which
vanilla files cannot confirm. binarize's `Member already defined` line is what `build.py` prints from
AddonBuilder's log when a build fails on a duplicate member.

Companion to the version note at the top of `pre-build-checks.md`. Folder structure, stringtable.csv,
include-list, and ODOL non-determinism still hold. This file is the 1.30
binarizer contract.

## Duplicate **members** abort binarize

Until 1.29 the pre-build check was "Duplicate class names: Same class cannot be
defined twice", and duplicate **properties** inside one class were silent, with the
last one winning. Since 1.30 the binarizer stops when a member is defined more than
once in a config file.

This is a **build blocker**. AddonBuilder / CfgConvert that used to succeed on
a repeated `scope`, `displayName`, `weight`, `hiddenSelections[]`, or an inner
class name now **stops**. The vanilla scripts hold no example of it: the check is
engine-side.

Audit every `config.cpp` (and inherited fragments) for a member
written twice in the **same class body**. Vanilla-style `class Foo; class Foo:
Bar {}` (forward + definition) is not the same bug; the stop is for
**multiple definitions of a member inside one block**.

Pre-build check 2 in `pre-build-checks.md` now covers both class names **and** members.

## Unpacked mods do not retire the PBO gate

Since 1.30, `-mod` can point at a folder and RV configs load
unpacked. That is a **diag iteration** path (`/dayz-launch-test`). Workshop /
dedicated shipping still needs a PBO. Do not skip AddonBuilder for a release
because unpacked load exists.

Navmesh `.nm` regeneration for 1.30 is a terrain/Workbench task, not
a PBO linter check. Flag it in the release notes of a custom map; this skill
does not validate `.nm` bytes.

## `fsShadowing`: a second PBO with a vanilla prefix (1.30 Update 2)

Since 1.30.164200 the PBO header property `fsShadowing=1` lets a PBO load even
when its prefix matches one already loaded, so its files can shadow vanilla
paths. Vanilla PBO headers do not carry it. A shadow PBO does not hide the
vanilla files it does not hold: with two holding only layouts, the rest of
vanilla `gui` still loaded on 1.30.164289
(`skills/dayz-ui-development/references/layout-variants-130.md` §2).

Measured on DayZDiag 1.30.164200 for a Workbench-generated layout variant: a PBO whose
`$PBOPREFIX$.txt` is the bare line `gui`, built by a third-party packer that
has an option to set the property, packed `config.bin`, the `.layout` and its `.layout.meta`,
and the header read back as `prefix=gui`, `fsShadowing=1`. It loaded unsigned
and the variant applied in game. A `config.cpp` was present. What the variant
does and how to author it:
`skills/dayz-ui-development/references/layout-variants-130.md`.

Checks for such a PBO: the header shows both properties; the PBO contains only
the files it means to shadow. A `.meta` beside each variant `.layout` is
optional, and so is `config.cpp`: variants packed without them applied on
1.30.164289 (`layout-variants-130.md` §1 and §3).

MakePbo writes the property too (MakePbo 2.16): a `$PBOPREFIX$.txt` holding the two lines
`prefix=gui` and `fsShadowing=1` gives the header `prefix=gui`,
`fsShadowing=1`, a stamp of MakePbo's own library and a `version=` stamp (the two
extra properties are MakePbo's own), with `config.cpp` compiled to `config.bin`
and the prefix file left out. Such PBOs loaded unsigned on DayZDiag
1.30.164289 and their variants applied. Without a `config.cpp`, MakePbo writes
no prefix. AddonBuilder (1.0.240639) has no option for the property: it writes
`product=dayz ugc` and `prefix`, and when the folder has no `config.cpp` it
packs an empty one and the prefix file.

FileBank, the DayZ Tools packer that
AddonBuilder calls (`Bin\PboUtils\FileBank.exe`; DayZ Tools Steam build
26405911), writes any property and needs no `config.cpp`:
`FileBank -property prefix=gui -property fsShadowing=1 -exclude <list file>
-dst <out folder> <folder>\gui` gave the header `prefix=gui`, `fsShadowing=1` and
nothing else, and a list file holding the line `$PBOPREFIX$.txt` kept the prefix
file out. The PBO is named after the source folder (`gui.pbo`). Such a PBO,
holding only a layout variant and installed under another name, loaded unsigned
on DayZDiag 1.30.164289 and its variant applied (`layout-variants-130.md` §3).
