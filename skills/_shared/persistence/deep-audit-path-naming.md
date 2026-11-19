# File name helpers that disagree

Covers mechanical check 1 of the deep audit (`deep-audit.md`): a path helper and a recovery or cleanup site that build different names for the same file, so the reader looks for a file the writer never wrote. Run it for any mod that builds names for its own save files.

Each helper looks right on its own; the bug is that two of them disagree. The helper names, suffixes and `file:line` values in the tables come from a third-party virtual storage mod. They show the shape of each table and are not vanilla facts. The search lines are patterns for the agent's own search tool: a regular expression, limited to `.c` files, printing matching lines with numbers.

## Example: `.tmp` against `.lfv.tmp`

In the virtual storage mod `GetContainerTmpPath(sid)` returned `container_<sid>.tmp`, while the recovery scan at boot looked for `container_<sid>.lfv.tmp`. Either name would have worked; the bug was that they differed. A crash in the middle of a write left a `.tmp` file that recovery never saw. Six reviews read both functions and passed them.

## List the path helpers

Find every function that returns a string ending in a known extension, and record its name, signature and the exact name it returns.

```text
Grep "function.*Path" --type c --output_mode content -n true
Grep "return.*\.lfv|return.*\.tmp|return.*\.bak|return.*\.json|return.*\.manifest" --type c --output_mode content -n true
```

Enforce Script has no `function` keyword, so the first pattern finds only comments. For helpers written as methods, also search for the declaration, for example `string\s+Get\w*Path\s*\(`.

| Helper | Signature | Returns | File:Line |
|---|---|---|---|
| `GetContainerLfvPath` | `(string sid)` | `<dir>/container_<sid>.lfv` | persistence.c:120 |
| `GetContainerTmpPath` | `(string sid)` | `<dir>/container_<sid>.tmp` | persistence.c:128 |
| `GetContainerBak1Path` | `(string sid)` | `<dir>/container_<sid>.lfv.bak1` | persistence.c:135 |
| `GetContainerBak2Path` | `(string sid)` | `<dir>/container_<sid>.lfv.bak2` | persistence.c:142 |

A name in the third column that breaks the pattern is a flag. Here `.tmp` breaks the `.lfv.<suffix>` pattern.

## List every name built inline

Find every string literal that ends in a known extension. This catches code that builds a path without the helper.

```text
Grep "\".*\.lfv\"|\".*\.tmp\"|\".*\.bak1\"|\".*\.bak2\"|\".*\.manifest\.json\"|\".*\.virtualizing\"|\".*\.restoring\"|\".*\.quarantine\.json\"" --type c --output_mode content -n true
```

Record the file, the line and the extension of each hit, and compare it with the helper table. Every mismatch is a finding.

## Match each reader to its writer

Find every call of each helper and sort the calls into writers and readers (recovery, cleanup, admin commands, the boot scan).

```text
Grep "GetContainerTmpPath|GetContainerLfvPath|GetContainerBak1Path|GetContainerBak2Path" --type c --output_mode content -n true
```

A writer and its reader must build exactly the same string. A writer that uses a helper while the reader uses an inline literal is a flag.

Every path a mod builds ends up as the argument of a vanilla file function, so search for those calls too; they show inline paths the suffix search missed, on both sides.

| Function | Source |
|---|---|
| `BeginParse` | `P:\scripts\1_core\proto\ensystem.c:392` |
| `FileExist`, `OpenFile` | `ensystem.c:397`, `:417` |
| `FindFile` (folder scan), `MakeDirectory` | `ensystem.c:520`, `:525` |
| `DeleteFile`, `CopyFile` | `ensystem.c:528`, `:531` |
| `FileSerializer.Open` | `P:\scripts\1_core\proto\serializer.c:108` |
| `JsonFileLoader` `LoadFile`, `SaveFile`, `JsonLoadFile`, `JsonSaveFile` | `P:\scripts\3_game\tools\jsonfileloader.c:7`, `:42`, `:105`, `:134` |

The list is not complete: a mod can also reach files through its own wrappers or a framework, so add those names.

## Report

| Site | Path built | Expected from the helper | File:Line |
|---|---|---|---|
| `RecoverFromTmp` | `container_<sid>.lfv.tmp` | `container_<sid>.tmp` | recovery.c:84 |

A mismatch on the recovery path is data loss; anywhere else it needs recovery.

Run the tables once per family of extensions:

- Main data: `.lfv`, or the mod's own main format.
- Temp files: `.tmp`, `.lfv.tmp`, `.partial`.
- Backups: `.bak`, `.bak1`, `.bak2`, `.lfv.bak1`.
- Markers: `.virtualizing`, `.restoring`, `.locked`, `.in-progress`.
- Side files: `.manifest.json`, `.quarantine.json`, `.meta`, `.health`.

Allow 5 to 10 minutes per family for a mod with 30 path call sites or fewer. When it takes longer, the mod builds too many paths inline, and the finding is to route them all through helpers before checking them for agreement.
