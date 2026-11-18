# Path-naming matrix: mechanical check 1

Catches the bug class where a path helper and a recovery or cleanup site disagree on the file name on disk: the reader looks for a file the writer never wrote, or the other way round. Open this in step 1 for any mod that builds file names for its own save files.

Reasoning agents miss this because each helper looks correct in isolation: the bug is the inconsistency, not any one site.

The helper names, suffixes and `file:line` values in the tables are from the virtual storage example (third-party mod); they show the shape of each table and are not vanilla facts. The search lines in the code blocks are recipes for the agent's search tool: a regular expression, limited to `.c` files, printing matching lines with numbers.

## Worked example: VULN-003 (virtual storage mod)

`GetContainerTmpPath(sid)` returned `container_<sid>.tmp`. The recovery boot scan looked for `container_<sid>.lfv.tmp`. Either naming was defensible; the bug was that they disagreed. Result: a crash in the middle of a virtualize left a `.tmp` on disk that recovery never noticed. Six reasoning agents read both functions and signed off.

## Procedure

### Step 1: inventory the path helpers

Search for every function that returns a string ending in a recognized extension. Record name, signature and exact return template.

```text
Grep "function.*Path" --type c --output_mode content -n true
Grep "return.*\.lfv|return.*\.tmp|return.*\.bak|return.*\.json|return.*\.manifest" --type c --output_mode content -n true
```

Enforce Script has no `function` keyword, so the first pattern only finds comments. For helpers written as methods, also search for the declaration shape, for example `string\s+Get\w*Path\s*\(`.

Build the table:

| Helper | Signature | Returns template | File:Line |
|---|---|---|---|
| `GetContainerLfvPath` | `(string sid)` | `<dir>/container_<sid>.lfv` | persistence.c:120 |
| `GetContainerTmpPath` | `(string sid)` | `<dir>/container_<sid>.tmp` | persistence.c:128 |
| `GetContainerBak1Path` | `(string sid)` | `<dir>/container_<sid>.lfv.bak1` | persistence.c:135 |
| `GetContainerBak2Path` | `(string sid)` | `<dir>/container_<sid>.lfv.bak2` | persistence.c:142 |

Inconsistency in the third column is a flag. In the example above, `.tmp` breaks the `.lfv.<suffix>` pattern.

### Step 2: inventory every extension concatenation

Search for every literal that ends in one of the recognized extensions. This finds places that build the path inline without going through a helper.

```text
Grep "\".*\.lfv\"|\".*\.tmp\"|\".*\.bak1\"|\".*\.bak2\"|\".*\.manifest\.json\"|\".*\.virtualizing\"|\".*\.restoring\"|\".*\.quarantine\.json\"" --type c --output_mode content -n true
```

For each hit, record the file and line and which extension is being built. Compare against the helper table. Any mismatch is a finding.

### Step 3: cross-reference reader sites against writer paths

For each helper, find every call site. Group by intent: writers against readers (recovery, cleanup, admin commands, boot scan).

```text
Grep "GetContainerTmpPath|GetContainerLfvPath|GetContainerBak1Path|GetContainerBak2Path" --type c --output_mode content -n true
```

For each writer and reader pair, the path they build must be byte-identical. If the writer uses `helper_A` and the reader uses an inline literal, that is a flag.

On the vanilla side, a path a mod builds ends up as the path argument of a vanilla file function. The common ones are `FileExist` (`P:\scripts\1_core\proto\ensystem.c:397`), `OpenFile` (`ensystem.c:417`), `FindFile` for directory scans (`ensystem.c:520`), `MakeDirectory` (`ensystem.c:525`), `DeleteFile` (`ensystem.c:528`), `CopyFile` (`ensystem.c:531`), `BeginParse` (`ensystem.c:392`), `FileSerializer.Open` (`P:\scripts\1_core\proto\serializer.c:108`), and the `JsonFileLoader` calls `LoadFile` (`P:\scripts\3_game\tools\jsonfileloader.c:7`), `SaveFile` (`jsonfileloader.c:42`), `JsonLoadFile` (`jsonfileloader.c:105`) and `JsonSaveFile` (`jsonfileloader.c:134`). This list is not exhaustive: a mod can also reach files through its own wrappers or a framework, so add those names too. Searching for these names finds inline paths the suffix search missed, on both the writer and the reader side.

### Step 4: output

Findings table:

| Site | Path constructed | Expected (per helper) | File:Line |
|---|---|---|---|
| RecoverFromTmp | `container_<sid>.lfv.tmp` | `container_<sid>.tmp` | recovery.c:84 |
| ... | | | |

Each row is a P0 if the path is on the data-loss recovery branch, P1 otherwise.

## Heuristics for what counts as an "extension"

Treat as one extension family per file (so the helper table groups them):

- **Authoritative data**: `.lfv` (or your equivalent main format)
- **Atomic temp**: `.tmp`, `.lfv.tmp`, `.partial`
- **Backups**: `.bak`, `.bak1`, `.bak2`, `.lfv.bak1`
- **Markers**: `.virtualizing`, `.restoring`, `.locked`, `.in-progress`
- **Sidecars**: `.manifest.json`, `.quarantine.json`, `.meta`, `.health`

Pick the family for your codebase and run the matrix once per family.

## Time budget

About 5 to 10 minutes per family on a mod of that size (30 path call sites or fewer). If it takes longer, the codebase has too many inline path constructions: the audit finding is then "consolidate path construction through helpers", before consistency is even checked.
