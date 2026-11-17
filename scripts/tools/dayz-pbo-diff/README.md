# dayz-pbo-diff

Compare the entries of two uncompressed PBOs by the SHA-256 of each entry's
payload, and their header properties. The question it answers: did the new
package change only what I meant to change?

An example of what it shows (not re-measured in this repo): rebuilding a 12 km
terrain package changed 51 entries, the WRP, `texHeaders.bin` and 49 textures,
while the water stayed the same.

## Run

Stdlib only, Python 3.10 or newer, no install. It runs from any directory, but
needs `scripts/tools/dayz-vehicle-proxy-contract` next to it: it imports that
tool's PBO reader by a path relative to its own file.

```powershell
python scripts/tools/dayz-pbo-diff/pbo_diff.py --old <old.pbo> --new <new.pbo> --out <diff.json>
python scripts/tools/dayz-pbo-diff/pbo_diff.py --old <old.pbo> --new <new.pbo> --out <diff.json> --ignore-prefix data/layers/
```

`--out` must not exist; the tool refuses to overwrite it. It writes nothing
else and never modifies either PBO.

| Exit | Meaning |
|---:|---|
| `0` | Both PBOs read and the report written, whatever it holds |
| `1` | An input refused or unreadable, or `--out` already exists; nothing written |
| `2` | Usage error |

stdout carries the same report with every list of 12 or more items replaced by
its count (`"51 items"`); the file keeps the lists whole.

## Report

| Key | Holds |
|---|---|
| `old`, `new` | The paths as given |
| `entries` | `[old count, new count]` |
| `props_equal` | Whether the header properties are the same list, in the same order |
| `props_old`, `props_new` | Those properties as `[name, value]` pairs, in file order |
| `only_old`, `only_new` | Entry names on one side only |
| `differing` | Every name whose payload differs, plus the names of `only_old` and `only_new`, sorted |
| `differing_count` | Its length |
| `ignored_prefixes` | The `--ignore-prefix` values as given |
| `differing_not_ignored` | `differing` without the names under those prefixes |

Names are printed with `/`. Old and new names are matched exactly once `\`
is turned into `/`: a case-only rename shows in both `only_old` and
`only_new`.

## What it compares, and what it does not

- **Payload bytes, through SHA-256.** The entry header fields are not compared:
  the same bytes under a new timestamp are equal.
- **Header properties as one ordered list.** The same pairs in another order
  are not equal.
- **`--ignore-prefix` filters a view, not the comparison.** It is repeatable,
  takes `/` or `\` and ignores case; `differing` still lists every name.
- **Compressed entries are refused, not decompressed.** The reader,
  `scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy/pbo.py` through
  `digest_pbo`, also refuses unsafe, duplicate and non-ASCII entry names, a
  malformed header, entry data past the end of the file, and bytes after the
  last entry other than a 21-byte trailer starting with `0x00`. A refusal is
  exit `1` with `error: <reason>` on stderr.
- **The trailing SHA-1 is neither compared nor checked.**

## Design decisions

- It reads through the fail-closed PBO reader of
  `scripts/tools/dayz-vehicle-proxy-contract` and has no PBO parser of its own.
- The reader returns the entry table and the header properties apart, so they
  are never told apart by size: a PBO with few entries, or with more
  properties than entries, is read correctly.
- No prefix is filtered by default. A prefix such as `data/layers/` is given
  with the repeatable `--ignore-prefix`.
- Bad input is a refusal with a non-zero exit, not an assert, and an existing
  `--out` is refused explicitly.
- The header properties are compared as one ordered list of pairs and
  reported (`props_old`, `props_new`). A dictionary comparison would ignore
  their order and keep a repeated name once.

## Tests

```powershell
python -m pytest scripts/tools/dayz-pbo-diff/tests -q
```

The PBOs are synthetic, written by the tests; stdlib only.
