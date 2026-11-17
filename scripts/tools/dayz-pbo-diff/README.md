# dayz-pbo-diff

Compare the entries of two uncompressed PBOs by the SHA-256 of each entry's
payload, and their header properties. The question it answers: did the new
package change only what I meant to change?

Reported with the tool (pipeline inbox fb-20261003-203108-9821, not re-measured
here): rebuilding a 12 km terrain package changed 51 entries, the WRP,
`texHeaders.bin` and 49 textures, while the water stayed the same.

## Run

Stdlib only, Python 3.10 or newer, no install. Run it from the pack tree: it
imports the PBO reader of `scripts/tools/dayz-vehicle-proxy-contract` by its own path.

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
  malformed header and entry data past the end of the file. A refusal is exit
  `1` with `error: <reason>` on stderr.
- **The trailing SHA-1 is neither compared nor checked.**

## Design decisions

- It reads through the Pack's fail-closed PBO reader instead of the project's
  own `read_pbo`, which is not adopted.
- The source told the entry table from the header properties by size, taking
  the dictionary of more than 100 items as the entries, so a PBO with 100
  entries or fewer was misread. The reader returns the two apart.
- Its one hard-coded filter (`data/layers/`) became the repeatable
  `--ignore-prefix`.
- Asserts became refusals with a non-zero exit, and an existing `--out` is
  refused explicitly.
- The header properties are compared as one ordered list of pairs and
  reported (`props_old`, `props_new`). The source compared them as a
  dictionary, which ignores their order and keeps a repeated name once.

## Tests

```powershell
python -m pytest scripts/tools/dayz-pbo-diff/tests -q
```

The PBOs are synthetic, written by the tests; stdlib only.
